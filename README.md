circa, a swiss army knife for encoding, decoding, and converting consumer IR codes

## Examples

### Convert high-level codes to broadlink or raw format

```
$ python -m circa convert -f broadlink rc5:1,10
broadlink:JgAUABsbNhsbHBsbGxsbNjYbGzY3NjYbAAAAAAAAAAA=
$ python -m circa convert -f raw rc5:1,10
raw:889,889,1778,889,889,889,889,889,889,889,889,1778,1778,889,889,1778,1778,1778,1778,889
```

### Decode a code automagically

```
$ python -m circa decode broadlink:JgBQAAABJZITNxMSExITEhMSExITEhMSExITNxI3EzcTNxM3EzcTNxMSEzcSNxMSExITEhMSExITNxMSExITNxI3EzcTNxM3EwAFEQABJkoTAA0FAAAAAAAAAAAAAAAA
100.0% raw:9621,4795,624,1806,624,591,624,591,624,591,624,591,623,592,623,592,623,592,623,592,623,1807,591,1806,624,1806,624,1806,623,1807,623,1807,623,1807,623,591,624,1806,592,1806,624,591,624,591,623,592,623,592,623,592,623,1807,623,592,623,591,624,1806,592,1806,624,1806,623,1807,623,1807,623,42591,9654,2430,624,109447
100.0% broadlink:JgBQAAABJZITNxMSExITEhMSExITEhMSExITNxI3EzcTNxM3EzcTNxMSEzcSNxMSExITEhMSExITNxMSExITNxI3EzcTNxM3EwAFEQABJkoTAA0FAAAAAAAAAAAAAAAA
94.9% nec:c=2,tp=621:01,06
90.2% nec:c=2:01,06
```

### Receive and decode codes from a Broadlink device

```
$ python -m circa receive -c 0 broadlink:0x27c2:192.168.10.42:c8f742001122
=== Received code ===
100.0% raw:9585,4827,657,591,657,591,657,624,624,623,624,624,624,624,657,591,657,1773,624,1773,657,591,657,1773,657,591,656,591,657,624,624,1773,657,1773,657,1773,624,624,657,591,657,591,656,592,656,1773,657,1773,657,591,657,591,657,1773,657,1773,657,1773,624,1773,657,624,624,624,656,1774,624,56776,9687,4860,656,591,657,624,624,624,657,591,656,592,656,624,624,624,657,1773,657,1773,657,591,657,1773,657,591,656,624,624,624,657,1773,657,1773,657,1773,624,624,657,591,656,624,624,1806,624,1806,624,1773,657,624,657,591,657,1773,657,1773,657,1773,657,591,656,624,624,624,657,1773,657,109447
99.8% broadlink:JgCQAAABJJMUEhQSFBMTExMTExMUEhQ2EzYUEhQ2FBIUEhQTEzYUNhQ2ExMUEhQSFBIUNhQ2FBIUEhQ2FDYUNhM2FBMTExQ2EwAGwQABJ5QUEhQTExMUEhQSFBMTExQ2FDYUEhQ2FBIUExMTFDYUNhQ2ExMUEhQTEzcTNxM2FBMUEhQ2FDYUNhQSFBMTExQ2FAANBQAAAAAAAAAAAAAAAA==
96.2% nec:tp=648,t0=608,t1=1776,ph=9636,a=2,bh=563,bl=563,bg=33780:80,c5,61;80,c5,71
90.4% nec:tp=648,a=2:80,c5,61;80,c5,71
84.9% nec:a=2:80,c5,61;80,c5,71
```

### Transmit a code with a Broadlink device

```
$ python -m circa transmit broadlink:0x27c2:192.168.10.42:c8f742001122 rc5:0,10
```

### Parse a complex code
```
$ python -m circa decode broadlink:JgBQAg0ODg4ODw0PDg4OAAM+cTkOKw4ODg4ODw0sDg4ODg4PDg4NLA4ODisOKw4ODisOKw4qDisOKw4ODg8OKg4PDg4ODw4ODg4ODw4ODQ8ODw4ODSwODg4rDg4ODw4ODisOKw4ODg4ODw4ODg8NDw4ODg8ODg4ODw4NDw0sDg4ODw4ODisOKw4qDg8ODg4rDisOKg4ABHBxOQ4rDg4ODg4PDioPDg4ODg8ODg4rDg4OKw4rDg4OKw4qDyoOKw4rDg4ODw4qDg8ODg4ODg8NDw4PDQ8NDw4PDg4ODg4rDg8NDw0PDRAOKg4PDg4ODw4ODQ8ODw0PDg4ODw4ODRAODg4ODg8NDw4ODg8ODg0QDSsODw4qDg8OKw4ODgAEb3I4DisODw4ODQ8OKw4ODw4NDw4PDSsODw4qDisODw4qDisOKw4rDioODw0PDSwODg4PDQ8NDw4PDg4NDw8ODg4ODw4ODQ8ODw0PDg4PDg4ODg8OKg4PDg4NLA4ODRANKw4PDg4ODw0rDisODg4rDg8ODg4ODg8ODg4ODg8ODg0QDg4ODg4PDQ8NDw4PDisODg4rDg4ODg8ODg4ODw4ODQ8ODw4ODg4ODw4ODRAODg0PDg8ODg4rDisODg4ODg8ODg4ODg8ODg4PDg4ODg4rDisODg4PDQ8ODg4PDQ8ODw0PDg4NEA4ODQ8ODw4ODg8ODg0PDisODg4PDg4NEA4ODisOKg4PDg4ODw4ODg4ODw4ODg4ODw4ODg8NDw4ODg8ODg4ODw4OKw4qDisODg8ODisODg4ADQUAAAAAAAAAAAAAAAA=
[...]
90.8% nec:tp=455,t0=477,t1=1407,ph=3722,pl=1860,a=-1,pi=120662,b=6,bh=449,bl=473,bg=27255:11,da,27,00,c5,00,10,e7;11,da,27,00,42,00,00,54;11,da,27,00,00,49,2c,00,a0,00,00,06,60,00,00,c1,00,00,4e
86.7% nec:tp=455,ph=3722,a=-1,pi=120662,b=6:11,da,27,00,c5,00,10,e7;11,da,27,00,42,00,00,54;11,da,27,00,00,49,2c,00,a0,00,00,06,60,00,00,c1,00,00,4e
```
