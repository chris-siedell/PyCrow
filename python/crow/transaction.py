# Crow Transaction Object
# 24 April 2018
# Chris Siedell
# project: https://pypi.org/project/crow-serial/
# source: https://github.com/chris-siedell/PyCrow


import crow.utils


class Transaction():
    """A class that holds information pertaining to a Crow transaction."""

    def __init__(self):

        self.address = 1
        self.port = 32
        self.command = None
        self.response_expected = True
        self.token = 0
        self.propcr_order = False
        
        self.response = None
        
        self.cmd_packet_buff = bytearray(2086) # 2086 is max command packet size
        self.cmd_packet_size = 0


    def new_command(self, address=1, port=32, command=None, response_expected=True, token=0, propcr_order=False):
        """Resets the transaction object with the parameters for a new command."""

        if address < 0 or address > 31:
            raise ValueError('address must be 0 to 31.')
    
        if port < 0 or port > 255:
            raise ValueError('port must be 0 to 255.')
    
        if address == 0 and response_expected:
            raise ValueError('Broadcast commands (address 0) must have response_expected=False.')
    
        if token < 0 or token > 255:
            raise ValueError('token must be 0 to 255.')
        
        if command is not None:
            cmd_size = len(command)
            if cmd_size > 2047:
                raise ValueError("The command payload must be 2047 bytes or less.")
            remainder = cmd_size%128
            cmd_body_size = (cmd_size//128)*130 + ((remainder + 2) if (remainder > 0) else 0)
        else:
            cmd_size = 0
            cmd_body_size = 0

        self.address = address
        self.port = port
        self.command = command
        self.response_expected = response_expected
        self.token = token
        self.propcr_order = propcr_order

        self.response = None
        
        # The command header is always 7 bytes.
        self.cmd_packet_size = 7 + cmd_body_size
   
        cmd_buff = self.cmd_packet_buff
         
        # CH0, CH1
        s = cmd_size.to_bytes(2, 'big')
        cmd_buff[0] = (s[0] << 3) | 1
        cmd_buff[1] = s[1]
    
        # CH2
        cmd_buff[2] = address
        if response_expected:
            cmd_buff[2] |= 0x80
    
        # CH3
        cmd_buff[3] = port
    
        # CH4
        cmd_buff[4] = token
    
        # CH5, CH6 
        check = crow.utils.fletcher16_checkbytes(cmd_buff[0:5])
        cmd_buff[5] = check[0]
        cmd_buff[6] = check[1]
   
        # Send the payload in chunks with up to 128 payload bytes followed by 2 F16 check bytes.
        buff_ind = 7
        cmd_rem = cmd_size
        cmd_ind = 0
        if propcr_order:
            # PropCR uses non-standard payload byte ordering (for command payloads only).
            while cmd_rem > 0:
                chk_size = min(cmd_rem, 128)
                cmd_rem -= chk_size
                start_buff_ind = buff_ind
    
                # In PropCR every group of up to 4 bytes is reversed (last group may be less than 4 bytes).
                chk_rem = chk_size
                while chk_rem > 0:
                    grp_size = min(chk_rem, 4)
                    chk_rem -= grp_size
                    cmd_buff[buff_ind:buff_ind+grp_size] = command[cmd_ind:cmd_ind+grp_size][::-1]
                    buff_ind += grp_size
                    cmd_ind += grp_size
                
                check = crow.utils.fletcher16_checkbytes(cmd_buff[start_buff_ind:buff_ind])
                cmd_buff[buff_ind] = check[0]
                cmd_buff[buff_ind+1] = check[1]
                buff_ind += 2
        else:
            # standard order
            while cmd_rem > 0:
                chk_size = min(cmd_rem, 128)
                cmd_rem -= chk_size
                next_cmd_ind = cmd_ind + chk_size
                cmd_slice = command[cmd_ind:next_cmd_ind]
                cmd_buff[buff_ind:buff_ind+chk_size] = cmd_slice
                buff_ind += chk_size
                check = crow.utils.fletcher16_checkbytes(cmd_slice)
                cmd_buff[buff_ind] = check[0]
                cmd_buff[buff_ind+1] = check[1]
                buff_ind += 2
                cmd_ind = next_cmd_ind
    


        
