#!/usr/bin/env python3
"""audio_synthesis_prepare - Prepare audio synthesis job for a text segment"""
import json, sys

def main():
    input_data = json.load(sys.stdin)
    result = {"result": "ok", "skill": "audio_synthesis_prepare", "input": input_data}
    print(json.dumps(result))

if __name__ == "__main__":
    main()
