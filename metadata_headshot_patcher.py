#!/usr/bin/python3
# metadata_headshot_patcher.py
import struct
import mmap
import hashlib
import os

class GlobalMetadataPatcher:
    def __init__(self, metadata_path):
        self.metadata_path = metadata_path
        with open(metadata_path, 'rb') as f:
            self.data = bytearray(f.read())
        
        # Parse header
        self.magic = struct.unpack('<I', self.data[0:4])[0]
        self.version = struct.unpack('<I', self.data[4:8])[0]
        
        print(f"[*] Magic: 0x{self.magic:X}")
        print(f"[*] Version: {self.version}")
    
    def find_string(self, target):
        """Cari string dalam string table"""
        # String table offset biasanya di offset 0x20
        string_table_offset = struct.unpack('<I', self.data[0x20:0x24])[0]
        string_count = struct.unpack('<I', self.data[0x24:0x28])[0]
        
        current_offset = string_table_offset
        for i in range(string_count):
            str_len = struct.unpack('<I', self.data[current_offset:current_offset+4])[0]
            string_data = self.data[current_offset+4:current_offset+4+str_len].decode('utf-8')
            
            if target.lower() in string_data.lower():
                print(f"[+] Found at index {i}: {string_data}")
                return current_offset
            
            current_offset += 4 + str_len + 1  # +1 untuk null terminator
        
        return None
    
    def patch_headshot_multiplier(self, multiplier=10.0):
        """Ubah damage multiplier untuk headshot"""
        # Cari string terkait damage
        damage_strings = [
            "headShotDamage",
            "HeadShotMultiplier",
            "CalculateHeadDamage",
            "DamageMultiplier"
        ]
        
        for string in damage_strings:
            offset = self.find_string(string)
            if offset:
                print(f"[*] Patching {string}...")
                
                # Cari referensi ke string ini di method table
                method_table_offset = struct.unpack('<I', self.data[0x40:0x44])[0]
                method_count = struct.unpack('<I', self.data[0x44:0x48])[0]
                
                # Iterate method table
                for i in range(method_count):
                    method_offset = method_table_offset + i * 20  # 20 bytes per method entry
                    
                    # Method name index
                    name_idx = struct.unpack('<I', self.data[method_offset:method_offset+4])[0]
                    
                    if name_idx == i:  # Index match dengan string kita
                        # Method signature - cari float constant
                        sig_idx = struct.unpack('<I', self.data[method_offset+12:method_offset+16])[0]
                        
                        # Patch float constant untuk multiplier
                        # Anggap kita menemukan offset float constant
                        float_offset = self.find_float_constant(method_offset)
                        if float_offset:
                            # Ganti dengan multiplier tinggi
                            packed = struct.pack('<f', multiplier)
                            self.data[float_offset:float_offset+4] = packed
                            print(f"[+] Patched multiplier to {multiplier}x at 0x{float_offset:X}")
                            return True
        
        print("[-] Could not find damage multiplier")
        return False
    
    def find_float_constant(self, method_offset):
        """Cari float constant dalam method"""
        # Cari di code section
        code_section_offset = struct.unpack('<I', self.data[0x60:0x64])[0]
        code_section_size = struct.unpack('<I', self.data[0x64:0x68])[0]
        
        # Scan untuk float pattern (ARM assembly)
        # LDR s0, [pc, #offset] untuk load float
        patterns = [
            b'\x00\x00\x90\xE5',  # LDR r0, [r0] (ARM)
            b'\x00\x00\xD0\xE5',  # LDRB r0, [r0] (ARM)
            b'\x00\x00\x9F\xE5',  # LDR r0, [pc, #offset] (ARM)
        ]
        
        for pattern in patterns:
            pos = self.data.find(pattern, code_section_offset, 
                               code_section_offset + code_section_size)
            if pos != -1:
                # Extract float value offset
                offset = struct.unpack('<I', self.data[pos+8:pos+12])[0]  # Anggap offset di +8
                float_offset = pos + 12 + offset  # PC relative offset
                return float_offset
        
        return None
    
    def patch_hitbox_detection(self):
        """Patch hitbox detection untuk selalu headshot"""
        # Cari method IsHeadshot atau CheckHitbox
        target_methods = [
            "IsHeadshot",
            "CheckHeadCollision",
            "GetHitboxType",
            "HitboxCollider"
        ]
        
        for method_name in target_methods:
            offset = self.find_string(method_name)
            if offset:
                print(f"[*] Patching {method_name}...")
                
                # Cari method yang menggunakan string ini
                method_table_offset = struct.unpack('<I', self.data[0x40:0x44])[0]
                method_count = struct.unpack('<I', self.data[0x44:0x48])[0]
                
                for i in range(method_count):
                    method_entry = method_table_offset + i * 20
                    name_idx = struct.unpack('<I', self.data[method_entry:method_entry+4])[0]
                    
                    # String table index comparison
                    string_idx = (offset - struct.unpack('<I', self.data[0x20:0x24])[0]) // 4
                    
                    if name_idx == string_idx:
                        # Method ditemukan, patch return value
                        # Cari IL2CPP method body
                        code_offset = self.get_method_code_offset(method_entry)
                        if code_offset:
                            # ARM assembly untuk selalu return true/headshot
                            # MOV r0, #1 ; BX lr
                            patch_code = b'\x01\x00\xA0\xE3\x1E\xFF\x2F\xE1'
                            self.data[code_offset:code_offset+len(patch_code)] = patch_code
                            print(f"[+] Patched {method_name} at 0x{code_offset:X}")
                            return True
        
        return False
    
    def get_method_code_offset(self, method_entry):
        """Dapatkan offset kode untuk method"""
        # Method entry: nameIdx, declaringTypeIdx, returnTypeIdx, 
        # parameterIdx, methodIndex, invokerIndex, token
        
        # Dapatkan method index
        method_idx = struct.unpack('<I', self.data[method_entry+16:method_entry+20])[0]
        
        # Cari di code registration table
        code_reg_table = struct.unpack('<I', self.data[0x80:0x84])[0]
        code_reg_count = struct.unpack('<I', self.data[0x84:0x88])[0]
        
        for i in range(code_reg_count):
            entry_offset = code_reg_table + i * 8
            idx = struct.unpack('<I', self.data[entry_offset:entry_offset+4])[0]
            code_ptr = struct.unpack('<I', self.data[entry_offset+4:entry_offset+8])[0]
            
            if idx == method_idx:
                # Convert RVA ke file offset
                return self.rva_to_offset(code_ptr)
        
        return None
    
    def rva_to_offset(self, rva):
        """Convert Relative Virtual Address to file offset"""
        # Ini simplification, implementasi sebenarnya kompleks
        # Asumsi metadata tidak di-pack
        return rva
    
    def add_autoaim_method(self):
        """Inject method baru untuk auto-aim ke kepala"""
        print("[*] Injecting auto-aim method...")
        
        # String baru untuk method kita
        new_method_name = "Internal_CalculateAutoAim"
        new_method_str = new_method_name.encode('utf-8') + b'\x00'
        
        # Tambah ke string table
        str_table_offset = struct.unpack('<I', self.data[0x20:0x24])[0]
        str_table_size = struct.unpack('<I', self.data[0x24:0x28])[0]
        
        # Append string
        new_str_offset = str_table_offset + str_table_size
        self.data[new_str_offset:new_str_offset+len(new_method_str)] = new_method_str
        
        # Update string table size
        new_size = str_table_size + len(new_method_str)
        self.data[0x24:0x28] = struct.pack('<I', new_size)
        
        print(f"[+] Added method string at 0x{new_str_offset:X}")
        
        # Tambah method entry
        method_table_offset = struct.unpack('<I', self.data[0x40:0x44])[0]
        method_count = struct.unpack('<I', self.data[0x44:0x48])[0]
        
        new_method_offset = method_table_offset + method_count * 20
        
        # Create method entry
        method_entry = bytearray(20)
        # nameIdx (index string baru)
        str_index = new_size // 4  # Approximate index
        struct.pack_into('<I', method_entry, 0, str_index)
        # declaringTypeIdx (PlayerController type)
        struct.pack_into('<I', method_entry, 4, 123)  # Contoh type index
        # returnTypeIdx (Vector3)
        struct.pack_into('<I', method_entry, 8, 456)  # Contoh return type
        # parameterIdx
        struct.pack_into('<I', method_entry, 12, 0)  # No parameters
        # methodIndex (baru)
        struct.pack_into('<I', method_entry, 16, method_count)
        # invokerIndex
        struct.pack_into('<I', method_entry, 20, 0)
        
        # Insert method entry
        self.data = self.data[:new_method_offset] + method_entry + self.data[new_method_offset:]
        
        # Update method count
        self.data[0x44:0x48] = struct.pack('<I', method_count + 1)
        
        print(f"[+] Added method entry at 0x{new_method_offset:X}")
        return True
    
    def save(self, output_path):
        """Save modified metadata"""
        with open(output_path, 'wb') as f:
            f.write(self.data)
        
        # Verify checksum jika perlu
        md5 = hashlib.md5(self.data).hexdigest()
        print(f"[+] Saved to {output_path}")
        print(f"[+] MD5: {md5}")
        
        return True

# Usage
if __name__ == "__main__":
    patcher = GlobalMetadataPatcher("global-metadata.dat")
    
    print("[*] Starting headshot patch...")
    
    # 1. Patch damage multiplier
    patcher.patch_headshot_multiplier(15.0)  # 15x damage
    
    # 2. Patch hitbox detection
    patcher.patch_hitbox_detection()
    
    # 3. Add auto-aim method (opsional)
    # patcher.add_autoaim_method()
    
    # 4. Save modified file
    patcher.save("global-metadata-patched.dat")
    
    print("[+] Patch completed!")
