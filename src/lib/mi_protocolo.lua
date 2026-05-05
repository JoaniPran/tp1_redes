fiuba_proto = Proto("fiuba_rdt", "Protocolo RDT")

-- Definir constantes para opcodes
local OPCODE_HANDSHAKE = 0
local OPCODE_DOWNLOAD = 1
local OPCODE_DATA = 2
local OPCODE_ACK = 3
local OPCODE_ERROR = 4
local OPCODE_CLOSE = 7

-- Tabla de nombres para opcodes
local opcode_names = {
    [0] = "HANDSHAKE (Upload)",
    [1] = "DOWNLOAD",
    [2] = "DATA",
    [3] = "ACK",
    [4] = "ERROR",
    [7] = "CLOSE (FIN)"
}

-- Definir Proto Fields
local f_opcode = ProtoField.uint8("fiuba_rdt.opcode", "Opcode", base.DEC)
local f_seq    = ProtoField.uint32("fiuba_rdt.seq", "Número de Secuencia", base.DEC)
local f_size   = ProtoField.uint16("fiuba_rdt.size", "Tamaño del Payload", base.DEC)
local f_payload = ProtoField.string("fiuba_rdt.payload", "Payload", base.ASCII)

fiuba_proto.fields = { f_opcode, f_seq, f_size, f_payload }

function fiuba_proto.dissector(buffer, pinfo, tree)
    if buffer:len() < 7 then return end

    pinfo.cols.protocol = "RDT"
    
    local opcode = buffer(0, 1):uint()
    local seq_num = buffer(1, 4):uint()
    local payload_size = buffer(5, 2):uint()
    
    -- Crear subtree principal
    local subtree = tree:add(fiuba_proto, buffer(0, 7 + payload_size), 
                             "Protocolo RDT (" .. (opcode_names[opcode] or "Unknown") .. ")")
    
    -- Agregar campos del header
    subtree:add(f_opcode, buffer(0, 1)):append_text(" (" .. (opcode_names[opcode] or "Unknown") .. ")")
    subtree:add(f_seq, buffer(1, 4))
    subtree:add(f_size, buffer(5, 2))
    
    -- Agregar payload si existe
    if payload_size > 0 then
        subtree:add(f_payload, buffer(7, payload_size))
    end
    
    -- Información en la columna info
    if opcode == OPCODE_HANDSHAKE then
        pinfo.cols.info = "HANDSHAKE"
    elseif opcode == OPCODE_DOWNLOAD then
        pinfo.cols.info = "DOWNLOAD"
    elseif opcode == OPCODE_DATA then
        pinfo.cols.info = "DATA Seq=" .. seq_num
    elseif opcode == OPCODE_ACK then
        pinfo.cols.info = "ACK Seq=" .. seq_num
    elseif opcode == OPCODE_ERROR then
        pinfo.cols.info = "ERROR"
    elseif opcode == OPCODE_CLOSE then
        pinfo.cols.info = "CLOSE"
    else
        pinfo.cols.info = "Unknown Opcode: " .. opcode
    end
end

-- Función heurística para detectar el protocolo RDT
function heuristic_checker(buffer, pinfo, tree)
    if buffer:len() < 7 then return false end
    
    local opcode = buffer(0, 1):uint()
    local payload_size = buffer(5, 2):uint()
    
    -- Validar que el tamaño del payload sea coherente
    if payload_size + 7 > buffer:len() then return false end
    
    -- Validaciones básicas por opcode
    if opcode == OPCODE_HANDSHAKE then
        if payload_size < 5 then return false end
        local payload_str = buffer(7, payload_size):string()
        return string.find(payload_str, "|") ~= nil
        
    elseif opcode == OPCODE_DOWNLOAD then
        return payload_size > 0 and payload_size < 256
        
    elseif opcode == OPCODE_DATA then
        return true
        
    elseif opcode == OPCODE_ACK then
        return payload_size <= 1
        
    elseif opcode == OPCODE_ERROR then
        return payload_size > 0 and payload_size < 256
        
    elseif opcode == OPCODE_CLOSE then
        return payload_size == 0
    end
    
    return false
end

-- Registrar con heurística permisiva (acepta todos los opcodes válidos sin validar payload format)
-- Esta se usa y parece funcionar
function heuristic_checker_permissive(buffer, pinfo, tree)
    if buffer:len() < 7 then return false end
    
    local opcode = buffer(0, 1):uint()
    local payload_size = buffer(5, 2):uint()
    
    -- Solo validar que el tamaño sea coherente
    if payload_size + 7 > buffer:len() then return false end
    
    -- Aceptar cualquier opcode válido (0, 1, 2, 3, 4, 7)
    if opcode == 0 or opcode == 1 or opcode == 2 or opcode == 3 or opcode == 4 or opcode == 7 then
        fiuba_proto.dissector(buffer, pinfo, tree)
        return true
    end
    
    return false
end

fiuba_proto:register_heuristic("udp", heuristic_checker_permissive)

-- También registrar específicamente en puerto 8080 por las dudas
local udp_port = DissectorTable.get("udp.port")
udp_port:add(8080, fiuba_proto)