# kamailio-logfile-analyzer
Retrieves SIP and softswitch KPI from proxy logs.

### Installation

1. Clone this repository.
2. Install a Python Virtual Environment:

    ```
    pyhton3 -m venv venv
    ```
3. Install dependencies running:

    ```
    pip install -r requirements.txt
    ```

### Usage

```
usage: analyze.py [-h] logfile [logfile ...]

Kamailio Proxy logfile parser

positional arguments:
  logfile     list of logfiles to parse

options:
  -h, --help  show this help message and exit
```

### Results

The output of the script will result in something like this:

```
                            09:00    10:00   11:00  12:00   14:00   15:00   16:00
PUBLISH request             59506   106290   45642    205   41902   57783   19999
PUBLISH reply              118489   211874   90836    406   83514  115124   39884
ACK request                 41640    70102   24851    151   28051   39712   13096
INVITE reply               122803   206502   73213    501   82322  114210   37896
INVITE B-leg                14724    24705    8856     58    9945   14071    4765
SUBSCRIBE request           12791    21701   20893    313   10436   20946   10384
INVITE A-leg                26853    45017   15815    127   18025   25575    8341
BYE reply                   16278    26987    9460     47   10713   14271    4645
NOTIFY reply                66767   106274   55138    404   48177   77038   29617
NOTIFY request               2476     4285    3486     34    1999    3802    1726
REGISTER request            21394    37358   37259    277   18413   37401   18869
INFO request                 5133     8191    2339     15    3155    4762    1297
BYE request                 20592    33944   10010     49   12562   15621    4876
Successfull calls            4462     7450    2709     12    2922    4065    1320
Total call time            669828  1180527  437603   1153  472452  635610  209727
ZDC (Zero Duration Calls)    4462     7450    2709     12    2922    4065    1320
Longest Call                 3037     6550    3578    515    3774    4561    4517
CANCEL reply                10132    18331    7394     39    6683    9287    3273
CANCEL request               8774    16004    6588     36    5820    8085    2883
Failed calls                 1815     3043    1226     10    1061    1264     474
PRACK request                 595      924     493      6     306     491     109
PRACK reply                   594      924     493      6     306     491     109
REFER request                  69      125      34      0      42      56      17
REFER reply                    69      125      34      0      42      56      17
UPDATE request                 28       48      21      0       8      15       4
UPDATE reply                   27       47      20      0       8      12       4
INFO reply                      6       16       8      0      10      28      16
Max CC                        323      360     137      1     275     204     112
ACD                           150      158     162     96     162     156     159
ASR                            17       17      17      9      16      16      16
Erlang                        186      328     122      0     131     177      58
MESSAGE request                 0        1       0      0       0       0       0
```
