#!/usr/bin/env python3

import json
import math
import gdb

from dataclasses import dataclass, field, asdict
from pprint import pprint

"""
This script enables visualization of the newlib nano heap allocator.
"""
def gdb_read_range(start:int, end:int) -> bytes:
    return gdb.selected_inferior() \
        .read_memory(start,
                     end - start) \
        .tobytes()

def gdb_read_bytes(value:gdb.Value) -> bytes:
    return gdb.selected_inferior() \
        .read_memory(int(value.address),
                     value.type.sizeof) \
        .tobytes()

# // --------------------------------------------------------

class MessageBoxNotFoundError(Exception):
    pass

@dataclass
class Header():
    address:int = 0
    magic:str = ""
    version:int = 0
    id:int = 0
    type:int = 0
    flags:int= 0
    len:int = 0
    crc32:int = 0
    
@dataclass
class Message():
    header: Header
    data: int = 0
    payload: str  = ""

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
                Message(
                    header = Header(                    
                        address = int(message.address),
                        magic = gdb_read_bytes(header["magic"]).hex(),
                        version = int(header["version"]),
                        id = int(header["id"]),
                        type = int(header["type"]),
                        flags = int(header["flags"]),
                        len = int(header["len"]),
                        crc32 = int(header["crc32"]),
                    ),
                    data = int(message["data"]),
                    payload = gdb_read_range(int(message["data"]), int(message["data"]) + int(header["len"])).hex()
                )
            )

        return messages
    
class MessageBoxes:
    def __init__(self):            
        inbox = gdb.parse_and_eval("inbox")
        if(inbox == 0):
            raise MessageBoxNotFoundError("Could not find inbox")
        
        self._inbox = MessageBox(inbox.dereference())
                
        outbox = gdb.parse_and_eval("outbox")
        if(outbox == 0):
            raise MessageBoxNotFoundError("Could not find outbox")
        
        self._outbox = MessageBox(outbox.dereference())
        
    @property
    def inbox(self):        
        return self._inbox.messages

    @property        
    def outbox(self):
        return self._outbox.messages
                        
# // --------------------------------------------------------

@dataclass
class Region:
    label:str = "Unknown"
    color:str = "#0679E4"
    start:int = 0
    end:int = 0
    blocks:dict = field(default_factory=dict)
    properties:dict = field(default_factory=dict)
    
    def initialize(self, callback):
        return callback(self)

@dataclass
class EmptyRegion(Region):
    label:str = "empty"
    color:str ="#9C9C96"

@dataclass
class FreeRegion(Region):
    label:str = "free_chunk"
    color:str ="#14D123"

@dataclass
class MessageRegion(Region):
    label:str = "message"
    color:str ="#DB1DA2"

@dataclass
class AllocatedRegion(Region):
    label:str ="allocated_chunk"
    color:str ="#FF0000"

@dataclass
class HeapRegion(Region):
    label:str ="heap"
    color:str ="#FF9900"

# // --------------------------------------------------------

class FreeListNotFoundError(Exception):
    pass


@dataclass
class Chunk:
    start:int = 0
    end:int = 0
    size:int = 0
    next:int = 0

    
class Heap:
    def __init__(self, msgbox:MessageBoxes):
        self.t_chunk = gdb.lookup_type("struct malloc_chunk")
        self.t_msg = gdb.lookup_type("struct msg")
        self.msgbox = msgbox
        
    def _update(self):
        free_list = gdb.parse_and_eval("__malloc_free_list")
        if(free_list == 0):
            raise FreeListNotFoundError("Could not find free list")
        
        self.free_list = free_list.dereference()

    @property
    def _free_chunks(self):
        # Try to update the list of free chunks. This can
        # fail if we have corrupted the pointer or if we
        # did not free any chunks yet.
        try:
            self._update()
        except FreeListNotFoundError:
            return []


        p = self.free_list
        r = p

        chunks = []
        while(r):
            c = Chunk(
                start = int(r.address),
                end = int(r.address) + int(r["size"]),
                size = int(r["size"]),
                next = int(r["next"]))

            chunks.append(c)
                        
            if(c.next != 0):
                r = gdb.Value(c.next).cast(self.t_chunk.pointer()).dereference()
            else:
                r = None

        return chunks
       
    @property
    def free(self):
        """
        Returns a list of free'ed memory regions
        """
        regions = []
        for chunk in self._free_chunks:
            regions.append(FreeRegion(                
                start = chunk.start,
                end = chunk.end,
                properties = {
                    "size": chunk.size,
                    "next": chunk.next
                }
            ))

        return regions
    
    @property
    def allocated(self):
        """
        Returns a list of allocated memory objects

            - Messages
            - Message data
        """

        # Map message messages and data
        regions = []
        for message in self.msgbox.inbox + self.msgbox.outbox:            
            regions.append(MessageRegion(
                start = message.header.address,
                end = message.header.address + self.t_msg.sizeof
            ))

            if message.data > 0:
                regions.append(AllocatedRegion(
                    label = f"Data message #{message.header.id}",
                    start = message.data,
                    end = message.data + message.header.len,
                    properties = {
                        "message.header.address": message.header.address,
                        "message.header.id": message.header.id,                        
                        "data": message.payload
                    }
                ))

        return regions
    
    @property    
    def regions(self):
        """
        Here we map all areas belonging to the heap
        that have not yet been mapped as free or
        allocated.
        """

        regions = []
        mapped_regions = sorted(self.free + self.allocated, key=lambda r: r.start)
        
        # If there are no mapped regions, then the entire
        # heap is mapped        
        if not len(mapped_regions):
            return [HeapRegion(                
                start = self.start,
                end = self.end
            )]

        # Add allocated chunk up until the first mapped region
        prev_region = mapped_regions[0]
        if mapped_regions[0].start > self.start:
            regions.append(HeapRegion(                
                start = self.start,
                end = mapped_regions[0].start
            ))
                        
            prev_region = regions[0]

        # Iterate over all mapped regions and add heap
        # regions in between        
        for region in mapped_regions:
            if prev_region.end < region.start:
                regions.append(HeapRegion(                
                start = prev_region.end,
                end = region.start
            ))
                
            regions.append(region)
            prev_region = region
                
        # Map remaining heap space
        if prev_region.end < self.end:
            regions.append(HeapRegion(                
                start = prev_region.end,
                end = self.end
            ))

        return regions
    
    @property
    def start(self):
        return int(gdb.parse_and_eval("__malloc_sbrk_start"))

    @property
    def end(self):
        return int(gdb.parse_and_eval("_sbrk(0)"))
    
    @property
    def size(self):
        return self.end - self.start
    

# // --------------------------------------------------------

def get_bootloader_state(region:Region):
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
                "#0300AD",
                int(gdb.parse_and_eval("&bootloader_unlocked")),
                int(gdb.parse_and_eval("&bootloader_unlocked")) + 4
        ).initialize(get_bootloader_state),
        Region("handlers",
                "#A84105",
                int(_handlers.address),
                int(_handlers.address) + _handlers_size
    )]

    def __init__(self, msgbox:MessageBoxes):
        self.heap = Heap(msgbox)

    @property
    def mem_blocks(self):
        return self.mem_size // self.blocksize
                        
    def _add_empty_regions(self, regions:list):
        padded_regions = []
        if not len(regions):
            return []

        # Fill memory up until the first region
        if regions[0].start > self.mem_start:
            padded_regions.append(EmptyRegion(                
                start = self.mem_start,
                end = regions[0].start
            ))

        # Loop through all regions and add empty memory
        # between adjacent regions
        prev_region = padded_regions[0]
        for region in regions:            
            if prev_region.end < region.start:

                # Map as a heap region if teh start
                # address is within boundaries
                if prev_region.end > self.heap.start and \
                    prev_region.end < self.heap.end:
                    padded_regions.append(HeapRegion(
                        start = prev_region.end,
                        end = region.start
                    ))
                else:
                    padded_regions.append(EmptyRegion(                    
                        start = prev_region.end,
                        end = region.start
                    ))
            
            padded_regions.append(region)
            prev_region = region
            
        # Fill memory space up until the end of memory        
        if prev_region.end < self.mem_end:
            padded_regions.append(EmptyRegion(                
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


    def _adjust_shared_block(self, regions):
        for i, region in enumerate(regions):
            if i + 1 < len(regions):
                next_region = regions[i + 1]
                if region.blocks["start"] == next_region.blocks["start"]:
                    if type(next_region) in [EmptyRegion, HeapRegion]:                       
                        next_region.blocks["total"] = 0

                    if type(region) in [EmptyRegion, HeapRegion]:
                        region.blocks["total"] = 0

    def _adjust_overlapping(self, regions):
        for i, region in enumerate(regions):
            if i + 1 < len(regions):
                next_region = regions[i + 1]
                if region.end > next_region.start:                    
                    region.end = next_region.start
                    self._add_block_metadata([region, next_region])


    def _adjust_empty(self, regions):
        for i, region in enumerate(regions):
            if region.blocks["total"] > 0:
                continue
            
            # Each region should be at least one block
            # in size
            region.blocks["total"] = 1

            # Try to "steal" a block from the
            # next region
            if i + 1 < len(regions):
                next_region = regions[i + 1]
                next_region.blocks["start"] += 1
                next_region.blocks["total"] -= 1

                region.blocks["start"] = region.blocks["end"]
                region.blocks["end"] = region.blocks["start"] + 1

            # Try to "steal" a block from the previous
            # region
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


    @property
    def regions(self):         
        _regions = []

        # Merge and sort all relevant regions
        _regions = sorted(self._pre_defined_regions +\
                          self.heap.regions,\
                           key=lambda r: r.start)
        
        # Apply padding for unallocated/undefined regions
        _regions = self._add_empty_regions(_regions)

        # Add block metadata, used for visualization
        self._add_block_metadata(_regions)

        # Adjust for overlapping and empty regions
        self._adjust_overlapping(_regions)
        self._adjust_empty(_regions)
        self._adjust_shared_block(_regions)

        # Perform some sanity checks
        self._check(_regions)
     
        return [asdict(r) for r in _regions]
    
# // --------------------------------------------------------

if __name__ == "__main__":
    mb = MessageBoxes()    
    mm = MemoryMap(mb)

    resp = {
        "mailbox": {
            "inbox": {
                "messages": [asdict(m) for m in mb.inbox]
            },

            "outbox": {
                "messages": [asdict(m) for m in mb.outbox]
            }
        },

        "memory": {
            "blocksize": mm.blocksize,
            "start": mm.mem_start,
            "end": mm.mem_end,  
            "blocks": mm.mem_blocks,
            "heap": {
                "start": mm.heap.start,
                "end": mm.heap.end,
                "blocks": mm.heap.size // mm.blocksize
            },
            "regions": mm.regions            
        }
    }

    print(json.dumps(resp))
