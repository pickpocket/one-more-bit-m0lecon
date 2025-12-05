#!/usr/bin/env python3
import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 24180

class Solver:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = None
        self.f = None

    def _log(self, msg: str):
        print(msg, file=sys.stderr)

    def connect(self):
        self.sock = socket.create_connection((self.host, self.port))
        self.f = self.sock.makefile('rw')
        self._log(f"[*] Connected to {self.host}:{self.port}")

    def close(self):
        if self.f: self.f.close()
        if self.sock: self.sock.close()

    def _cmd(self, cmd: dict) -> dict:
        json.dump(cmd, self.f)
        self.f.write('\n')
        self.f.flush()
        resp = self.f.readline()
        if not resp: raise ConnectionError("Connection lost")
        return json.loads(resp)

    def solve_round(self, round_id):
        resp = self._cmd({"command": "encrypt", "m0": 0.0, "m1": 100.0})
        c0 = resp["state_index"]

        # Double square to amplify noise
        c1 = self._cmd({"command": "eval", "function": "square", "indices": [c0]})["state_index"]
        c2 = self._cmd({"command": "eval", "function": "square", "indices": [c1]})["state_index"]

        # Count set bits in low-order positions (noise region)
        set_bits = 0
        probes = 40
        for i in range(probes):
            resp = self._cmd({"command": "decrypt", "index": c2, "position": i})
            if resp.get("status") == "ok" and resp["bit"] == 1:
                set_bits += 1
        
        # With 100^4, case 1 will have ~50% random bits
        # Case 0 will still have nearly all zeros
        threshold = 8  # Can be even lower now due to dramatic difference
        guess = 1 if set_bits > threshold else 0
        
        self._log(f"    Round {round_id}: {set_bits}/{probes} bits set -> Guessed {guess}")

        res = self._cmd({"command": "guess", "bit": guess})
        if res["result"] != "WIN":
             raise RuntimeError(f"Lost round {round_id}")
        return True

    def run(self):
        self.connect()
        try:
            while True:
                line = self.f.readline()
                if not line: break
                msg = json.loads(line)
                
                if msg.get("status") == "new_round":
                    round_id = msg["round"]
                    print(f"[*] Round {round_id}...", end=" ", flush=True)
                    self.solve_round(round_id)
                    print("WIN")
                elif "flag" in msg:
                    print(f"\n\n[!!!] FLAG: {msg['flag']}\n")
                    return
        finally:
            self.close()

if __name__ == "__main__":
    Solver(HOST, PORT).run()