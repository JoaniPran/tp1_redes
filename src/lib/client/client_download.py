import socket
import os

from lib.datagrams.datagram import Datagram
from lib.datagrams.download import DownloadRequestDatagram
from lib.datagrams.ack import AckDatagram
from lib.datagrams.error import ErrorDatagram
from lib.protocols.stop_and_wait import StopAndWaitProtocol
from lib.protocols.selective_repeat import SelectiveRepeatProtocol
from lib.client.base_client import ClientStrategy
from lib.constants import SOCKET_RECV_BUFFER, SW_STRATEGY, SR_STRATEGY, REQUEST_TIMEOUT


class ClientDownloader(ClientStrategy):
    def download_file(self, remote_name: str, local_path: str):
        os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)

        self._request_phase(remote_name)

        if self.protocol_name == SR_STRATEGY:
            protocol = SelectiveRepeatProtocol(self.sock, self.server_addr, self.logger)
        elif self.protocol_name == SW_STRATEGY:
            protocol = StopAndWaitProtocol(self.sock, self.server_addr, self.logger)
        else:
            raise ValueError(f"Protocol '{self.protocol_name}' is not supported. Use 'sw' or 'sr'.")
        protocol.receive_file(local_path, expected_seq=1)


        self.logger.info(f"File successfully saved to {local_path}")
        self.sock.close()

    def _request_phase(self, remote_name: str):
        self.logger.debug(f"Sending download request for: {remote_name} via {self.protocol_name}")
        self.sock.settimeout(REQUEST_TIMEOUT)
        request_packet = DownloadRequestDatagram(remote_name, self.protocol_name)
        bytes_to_send = request_packet.to_bytes()

        attempts = 0
        while attempts < self.max_attempts:
            self.sock.sendto(bytes_to_send, self.server_addr)
            try:
                data, new_addr = self.sock.recvfrom(SOCKET_RECV_BUFFER)
                response = Datagram.from_bytes(data)

                if isinstance(response, ErrorDatagram):
                    self.logger.error(f"Server rejected download: {response.message}")
                    raise ConnectionError(f"Server error: {response.message}")

                if isinstance(response, AckDatagram) and response.seq_num == 0:
                    self.server_addr = new_addr
                    self.logger.debug(f"Request accepted by Worker at {new_addr}")
                    return
            except socket.timeout:
                attempts += 1
                self.logger.warning(f"Retrying request ({attempts}/{self.max_attempts})")

        raise ConnectionError("Server did not respond to the download request.")