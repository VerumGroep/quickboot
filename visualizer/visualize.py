#!/usr/bin/env python3

import json
import math
import gdb

from dataclasses import dataclass, field, asdict
from pprint import pprint

"""
This script enables visualization of newlib nano heap allocator.
"""

def gdb_read_bytes(value:gdb.Value) -> bytes:
    return gdb.selected_inferior() \
        .read_memory(int(value.address),
                     value.type.sizeof) \
        .tobytes()

# // --------------------------------------------------------

class MailboxNotFoundError(Exception):
    pass


class MessageBox:    
    def __init__(self, mbox):
        self.mbox = mbox
        
    @property
    def messages(self):
        messages = []
        for i in range(0, self.mbox["num_messages"]):
            message = self.mbox["messages"][i]
            header = message["header"]

            messages.append(
                {
                    "header": {
                        "address": int(message.address),
                        "magic": gdb_read_bytes(header["magic"]).hex(),
                        "version": int(header["version"]),
                        "id": int(header["id"]),
                        "type": int(header["type"]),
                        "flags": int(header["flags"]),
                        "len": int(header["len"]),
                        "crc32": int(header["crc32"]),
                    }, "data": gdb_read_bytes(message["data"]).hex()                    
                }
            )

        return messages
                        
# // --------------------------------------------------------

class FreeListNotFoundError(Exception):
    pass


class Heap:
    def __init__(self):
        self.t_chunk = gdb.lookup_type("struct malloc_chunk")
        
    def _update(self):
        free_list = gdb.parse_and_eval("__malloc_free_list")
        if(free_list == 0):
            raise FreeListNotFoundError("Could not find free list")
        
        self.free_list = free_list.dereference()

    def _list_free(self):
        self._update()
        p = self.free_list
        r = p

        chunks = []
        while(r):
            c = {"address": r.address,
                 "size": int(r["size"]),
                 "next": int(r["next"])}
            
            chunks.append(c)            
            if(c["next"] != 0):
                r = gdb.Value(c["next"]).cast(self.t_chunk.pointer()).dereference()
            else:
                r = None

        return chunks
    
    def add_regions(self, regions):
        """
        This function will add heap specific regions to the
        memory map. These include:

            - Chunks on the free list
            - Allocated chunks
            - End of the heap
        """
        return regions
    
    @property
    def start(self):
        return int(gdb.parse_and_eval("__malloc_sbrk_start"))

    @property
    def end(self):
        return int(gdb.parse_and_eval("_sbrk(0)"))

# // --------------------------------------------------------

@dataclass
class Region:
    label:str = "Unknown"
    color:str = "#FF0000"
    start:int = 0
    end:int = 0
    blocks:dict = field(default_factory=dict)
    properties:dict = field(default_factory=dict)
    
    def initialize(self, callback):
        return callback(self)
                
def get_bootloader_state(region):
    region.properties = {
        "value": int(gdb.parse_and_eval("bootloader_unlocked"))
    }

    return region


class MemoryMap:
    # SRAM properties
    blocksize = 0x20
    mem_start = 0x20000000
    mem_size = 0x5000
    mem_end = mem_start + mem_size
    
    """
    This section defines the regions which need to visualized
    """
    _handlers = gdb.parse_and_eval("handlers").dereference()
    _handler = gdb.lookup_type("struct msg_handler")
    _handlers_size = int(_handlers["num_handlers"]) * _handler.sizeof

    _pre_defined_regions = [
        Region("bootloader_unlocked",
                "#26032E",
                int(gdb.parse_and_eval("&bootloader_unlocked")),
                int(gdb.parse_and_eval("&bootloader_unlocked")) + 4
        ).initialize(get_bootloader_state),
        Region("handlers",
                "#0E0565",
                int(_handlers.address),
                int(_handlers.address) + _handlers_size
    )]

    def __init__(self):
        self.heap = Heap()

    @property
    def mem_blocks(self):
        return self.mem_size // self.blocksize
                        
    def _add_empty_regions(self, regions:list):
        padded_regions = []
        if not len(regions):
            return []

        # Fill memory up until the first region
        if regions[0].start > self.mem_start:
            padded_regions.append(Region(
                label="empty",
                start=self.mem_start,
                end=regions[0].start
            ))

        # Loop through all regions and add empty memory
        # between adjacent regions
        prev_region = padded_regions[0]
        for region in regions:            
            if prev_region.end < (region.start - self.blocksize):
                padded_regions.append(Region(
                    label="empty",
                    start=prev_region.end,
                    end=region.start
                ))
            
            padded_regions.append(region)
            prev_region = region
            
        # Fill memory space up until the end of memory        
        if prev_region.end < self.mem_end:
            padded_regions.append(Region(
                label="empty",
                start=prev_region.end,
                end=self.mem_end
            ))

        return padded_regions
    

    def _add_block_metadata(self, regions):
        for region in regions:
            start_block = (region.start - self.mem_start) // self.blocksize
            end_block = (region.end - self.mem_start) // self.blocksize

            region.blocks = {
                "start": start_block,
                "end": end_block,
                "total": end_block - start_block,
            }

    def _adjust_regions(self, regions):
        for i, region in enumerate(regions):
            if region.blocks["total"] > 0:
                continue

            region.blocks["total"] = 1

            if i + 1 < len(regions):
                next_region = regions[i + 1]
                next_region.blocks["start"] += 1
                next_region.blocks["total"] -= 1

                region.blocks["start"] = region.blocks["end"]
                region.blocks["end"] = region.blocks["start"] + 1

            elif i > 0:
                prev_region = regions[i - 1]
                prev_region.blocks["end"] -= 1
                prev_region.blocks["total"] -= 1

                region.blocks["end"] = region.blocks["start"] + 1

 
    def _check(self, regions):

        """
        Check 1: Add all bytes from each regions and compare
        with the total memory size

        Check 2: Add all blocks from each region and compare
        with total number of expected block
        """
        total_bytes = 0
        total_blocks = 0
        for region in regions:
            total_bytes += region.end - region.start
            total_blocks += region.blocks["total"]

        try:
            assert(total_bytes == self.mem_size)
            assert(total_blocks == self.mem_blocks)
        except AssertionError:
            print(f"{total_bytes=} {self.mem_size=}")
            print(f"{total_blocks=} {self.mem_blocks=}")
            return
            
    @property
    def regions(self):         
        _regions = []

        # Sort, add empty regions and block meta data
        _regions = sorted(self._pre_defined_regions, key=lambda r: r.start)
        _regions = self.heap.add_regions(_regions)
        _regions = self._add_empty_regions(_regions)
        self._add_block_metadata(_regions)
        self._adjust_regions(_regions)

        # Perform
        self._check(_regions)
     
        return [asdict(r) for r in _regions]
    
# // --------------------------------------------------------

class Visualize:
    def __init__(self):            
        inbox = gdb.parse_and_eval("inbox")
        if(inbox == 0):
            raise MailboxNotFoundError("Could not find inbox")
        
        self.inbox = MessageBox(inbox.dereference())
                
        outbox = gdb.parse_and_eval("outbox")
        if(outbox == 0):
            raise MailboxNotFoundError("Could not find outbox")
        
        self.outbox = MessageBox(outbox.dereference())
        
    def list_inbox(self):        
        return self.inbox.messages
        
    def list_outbox(self):
        return self.outbox.messages


if __name__ == "__main__":
    v = Visualize()    
    mm = MemoryMap()

    resp = {
        "mailbox": {
            "inbox": {
                "messages": v.list_inbox()
            },

            "outbox": {
                "messages": v.list_outbox()
            }
        },

        "memory": {
            "blocksize": mm.blocksize,
            "start": mm.mem_start,
            "end": mm.mem_end,  
            "blocks": mm.mem_blocks,
            "regions": mm.regions
        }
    }

    print(json.dumps(resp))
