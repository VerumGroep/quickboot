#!/usr/bin/env python3

import json
import gdb


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
        
    def update(self):
        free_list = gdb.parse_and_eval("__malloc_free_list")
        if(free_list == 0):
            raise FreeListNotFoundError("Could not find free list")
        
        self.free_list = free_list.dereference()

    def list_free(self):
        self.update()
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
    
    @property
    def start(self):
        return int(gdb.parse_and_eval("__malloc_sbrk_start"))

    @property
    def end(self):
        return int(gdb.parse_and_eval("_sbrk(0)"))

# // --------------------------------------------------------

class MemoryMap:
    # SRAM properties
    blocksize = 0x20
    mem_start = 0x20000000
    mem_size = 0x5000
    mem_end = mem_start + mem_size
    
    """
    This section defines the regions which need to visualized
    """
    pre_defined_regions = [{
        "label": "heap",        
        "color": "#FF0000",
        "start": 0,
        "end": 0,
        "blocks": 0,
        "properties": {}        
    }]

    def __init__(self):
        self.heap = Heap()
        
    def calc_blocks(self, start: int, end: int) -> int:
        bs = ((end - start) // self.blocksize)
        if ((end -start) % self.blocksize):
            bs += 1

        return bs

    @property
    def regions(self):         
        regions = []

        # Update heap values
        for index in range(len(self.pre_defined_regions)):
            region = self.pre_defined_regions[index]

            if region["label"] == "heap":
                # Set global start and end
                self.pre_defined_regions[index]["start"] = self.heap.start
                self.pre_defined_regions[index]["end"] = self.heap.end
                self.pre_defined_regions[index]["blocks"] = self.calc_blocks(self.heap.start, self.heap.end)

        # Sort on start address
        regions_sorted = sorted(self.pre_defined_regions, key=lambda r: r["start"])

        # Fill final map with empty blocks
        address = self.mem_start        
        for region in regions_sorted:
            # Check for unallocated blocks between current region
            # and previous address
            if address < region["start"]:
                regions.append({
                    "label": "empty",
                    "color": "#808080",
                    "start": address,
                    "end": region["start"],
                    "blocks": self.calc_blocks(address, region["start"]),
                    "properties": {}
                })

            # Append region
            regions.append(region)

            # Update last address
            address = region["end"]

        if address < self.mem_end:
            regions.append({
                "label": "empty",
                "color": "#808080",
                "start": address,
                "end": self.mem_end,
                "blocks": self.calc_blocks(address, self.mem_end),
                "properties": {}
            })
        
        return regions
    
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
            "blocks": mm.mem_size // mm.blocksize,
            "regions": mm.regions
        }
    }

    print(json.dumps(resp))