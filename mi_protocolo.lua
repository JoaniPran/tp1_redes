fiuba_proto = Proto("fiuba_rdt", "Protocolo RDT")

local f_opcode = ProtoField.uint8("fiuba_rdt.opcode", "Opcode", base.DEC)
local f_seq    = ProtoField.uint32("fiuba_rdt.seq", "Numero de Secuencia", base.DEC)
local f_size   = ProtoField.uint16("fiuba_rdt.size", "Tamaño del Payload", base.DEC)
local f_data   = ProtoField.string("fiuba_rdt.data", "Datos / Payload")

fiuba_proto.fields = { f_opcode, f_seq, f_size, f_data }

function fiuba_proto.dissector(buffer, pinfo, tree)
    if buffer:len() <= 7 then return end

    pinfo.cols.protocol = "RDT-TP"
    local subtree = tree:add(fiuba_proto, buffer(), "Cabecera RDT")

    subtree:add(f_opcode, buffer(0, 1))
    subtree:add(f_seq,    buffer(1, 4))
    subtree:add(f_size,   buffer(5, 2))

    if buffer:len() > 7 then
        local payload_length = buffer:len() - 7
        subtree:add(f_data,   buffer(7, payload_length))

        local op_val = buffer(0,1):uint()
        if op_val == 0 then
            pinfo.cols.info = "UPLOAD Request - " .. buffer(7, payload_length):string()
        elseif op_val == 2 then
            pinfo.cols.info = "DATOS - Secuencia: " .. buffer(1,4):uint()
        elseif op_val == 3 then
            pinfo.cols.info = "ACK - Secuencia: " .. buffer(1,4):uint()
        end
    end
end

local udp_port = DissectorTable.get("udp.port")
udp_port:add(8080, fiuba_proto)