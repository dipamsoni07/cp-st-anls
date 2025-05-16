# Connection established
mark_info = {
  "type": "market_info",
  "currentTs": "1742373997647",
  "marketInfo": {
    "segmentStatus": {
      "NCD_FO": "NORMAL_OPEN",
      "BCD_FO": "NORMAL_OPEN",
      "NSE_INDEX": "NORMAL_OPEN",
      "NSE_EQ": "NORMAL_OPEN",
      "BSE_INDEX": "NORMAL_OPEN",
      "BSE_FO": "NORMAL_OPEN",
      "MCX_FO": "NORMAL_OPEN",
      "NSE_FO": "NORMAL_OPEN",
      "NSE_COM": "NORMAL_OPEN",
      "BSE_EQ": "NORMAL_OPEN",
      "MCX_INDEX": "NORMAL_OPEN"
    }
  }
}

print("marketInfo" in mark_info)
print(mark_info["marketInfo"]["segmentStatus"]["NSE_EQ"])

# --------------------------------------------------
data_dict = {
  "feeds": {
    "NSE_EQ|INE090A01021": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {
            "ltp": 1313.7,
            "ltt": "1742373997241",
            "ltq": "245",
            "cp": 1309.85
          },
          "marketLevel": {
            "bidAskQuote": [
              {
                "bidQ": "570",
                "bidP": 1313.65,
                "askQ": "746",
                "askP": 1313.7
              },
              {
                "bidQ": "366",
                "bidP": 1313.6,
                "askQ": "700",
                "askP": 1313.75
              },
              {
                "bidQ": "384",
                "bidP": 1313.55,
                "askQ": "2020",
                "askP": 1313.8
              },
              {
                "bidQ": "209",
                "bidP": 1313.5,
                "askQ": "1",
                "askP": 1313.85
              },
              {
                "bidQ": "65",
                "bidP": 1313.45,
                "askQ": "1",
                "askP": 1313.9
              }
            ]
          },
          "optionGreeks": {},
          "marketOHLC": {
            "ohlc": [
              {
                "interval": "1d",
                "open": 1305.6,
                "high": 1316.2,
                "low": 1302.15,
                "close": 1313.7,
                "vol": "7790518",
                "ts": "1742322600000"
              },
              {
                "interval": "I1",
                "open": 1312.75,
                "high": 1313.45,
                "low": 1312.6,
                "close": 1313.1,
                "vol": "45682",
                "ts": "1742373900000"
              }
            ]
          },
          "atp": 1310.68,
          "vtt": "7790518",
          "tbq": 359157.0,
          "tsq": 421241.0
        }
      },
      "requestMode": "full_d5"
    }
  },
  "currentTs": "1742373998670"
}

print("NSE_EQ|INE090A01021" in data_dict['feeds'])

# --------------------------------------------------
{
  "type": "live_feed",
  "feeds": {
    "NSE_EQ|INE090A01021": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {
            "ltp": 1313.7,
            "ltt": "1742373998758",
            "ltq": "234",
            "cp": 1309.85
          },
          "marketOHLC": {
            "ohlc": [
              {
                "interval": "1d",
                "open": 1305.6,
                "high": 1316.2,
                "low": 1302.15,
                "close": 1313.7,
                "vol": "7791920",
                "ts": "1742322600000"
              },
              {
                "interval": "I1",
                "open": 1312.75,
                "high": 1313.45,
                "low": 1312.6,
                "close": 1313.1,
                "vol": "45682",
                "ts": "1742373900000"
              }
            ]
          },
          "atp": 1310.68,
          "vtt": "7791920",
          "tbq": 358719.0,
          "tsq": 419843.0
        }
      },
      "requestMode": "full_d5"
    }
  },
  "currentTs": "1742373998921"
}
# --------------------------------------------------
{
  "type": "live_feed",
  "feeds": {
    "NSE_EQ|INE090A01021": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {
            "ltp": 1313.7,
            "ltt": "1742373999660",
            "ltq": "57",
            "cp": 1309.85
          },
          "marketLevel": {
            "bidAskQuote": [
              {
                "bidQ": "469",
                "bidP": 1313.65,
                "askQ": "1087",
                "askP": 1313.7
              },
              {
                "bidQ": "366",
                "bidP": 1313.6,
                "askQ": "278",
                "askP": 1313.75
              },
              {
                "bidQ": "431",
                "bidP": 1313.55,
                "askQ": "701",
                "askP": 1313.85
              },
              {
                "bidQ": "260",
                "bidP": 1313.5,
                "askQ": "1",
                "askP": 1313.9
              },
              {
                "bidQ": "9",
                "bidP": 1313.45,
                "askQ": "859",
                "askP": 1313.95
              }
            ]
          },
          "optionGreeks": {},
          "marketOHLC": {
            "ohlc": [
              {
                "interval": "1d",
                "open": 1305.6,
                "high": 1316.2,
                "low": 1302.15,
                "close": 1313.7,
                "vol": "7791920",
                "ts": "1742322600000"
              },
              {
                "interval": "I1",
                "open": 1312.75,
                "high": 1313.45,
                "low": 1312.6,
                "close": 1313.1,
                "vol": "45682",
                "ts": "1742373900000"
              }
            ]
          },
          "atp": 1310.68,
          "vtt": "7792028",
          "tbq": 358719.0,
          "tsq": 419843.0
        }
      },
      "requestMode": "full_d5"
    }
  },
  "currentTs": "1742373999822"
}
# --------------------------------------------------
{
  "type": "live_feed",
  "feeds": {
    "NSE_EQ|INE090A01021": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {
            "ltp": 1313.65,
            "ltt": "1742373999872",
            "ltq": "2",
            "cp": 1309.85
          },
          "marketLevel": {
            "bidAskQuote": [
              {
                "bidQ": "811",
                "bidP": 1313.65,
                "askQ": "594",
                "askP": 1313.7
              },
              {
                "bidQ": "366",
                "bidP": 1313.6,
                "askQ": "664",
                "askP": 1313.75
              },
              {
                "bidQ": "241",
                "bidP": 1313.55,
                "askQ": "701",
                "askP": 1313.85
              },
              {
                "bidQ": "269",
                "bidP": 1313.5,
                "askQ": "1",
                "askP": 1313.9
              },
              {
                "bidQ": "383",
                "bidP": 1313.4,
                "askQ": "159",
                "askP": 1313.95
              }
            ]
          },
          "optionGreeks": {},
          "marketOHLC": {
            "ohlc": [
              {
                "interval": "1d",
                "open": 1305.6,
                "high": 1316.2,
                "low": 1302.15,
                "close": 1313.65,
                "vol": "7792028",
                "ts": "1742322600000"
              },
              {
                "interval": "I1",
                "open": 1312.75,
                "high": 1313.45,
                "low": 1312.6,
                "close": 1313.1,
                "vol": "45682",
                "ts": "1742373900000"
              }
            ]
          },
          "atp": 1310.68,
          "vtt": "7792030",
          "tbq": 358867.0,
          "tsq": 419774.0
        }
      },
      "requestMode": "full_d5"
    }
  },
  "currentTs": "1742373999970"
}
# --------------------------------------------------
{
  "type": "live_feed",
  "feeds": {
    "NSE_EQ|INE090A01021": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {
            "ltp": 1313.65,
            "ltt": "1742374000570",
            "ltq": "5",
            "cp": 1309.85
          },
          "marketLevel": {
            "bidAskQuote": [
              {
                "bidQ": "811",
                "bidP": 1313.65,
                "askQ": "594",
                "askP": 1313.7
              },
              {
                "bidQ": "366",
                "bidP": 1313.6,
                "askQ": "664",
                "askP": 1313.75
              },
              {
                "bidQ": "241",
                "bidP": 1313.55,
                "askQ": "701",
                "askP": 1313.85
              },
              {
                "bidQ": "269",
                "bidP": 1313.5,
                "askQ": "1",
                "askP": 1313.9
              },
              {
                "bidQ": "383",
                "bidP": 1313.4,
                "askQ": "159",
                "askP": 1313.95
              }
            ]
          },
          "optionGreeks": {},
          "marketOHLC": {
            "ohlc": [
              {
                "interval": "1d",
                "open": 1305.6,
                "high": 1316.2,
                "low": 1302.15,
                "close": 1313.65,
                "vol": "7792028",
                "ts": "1742322600000"
              },
              {
                "interval": "I1",
                "open": 1312.75,
                "high": 1313.45,
                "low": 1312.6,
                "close": 1313.1,
                "vol": "45682",
                "ts": "1742373900000"
              }
            ]
          },
          "atp": 1310.68,
          "vtt": "7792081",
          "tbq": 358867.0,
          "tsq": 419774.0
        }
      },
      "requestMode": "full_d5"
    }
  },
  "currentTs": "1742374000871"
}
# --------------------------------------------------
{
  "type": "live_feed",
  "feeds": {
    "NSE_EQ|INE090A01021": {
      "fullFeed": {
        "marketFF": {
          "ltpc": {
            "ltp": 1313.65,
            "ltt": "1742374000570",
            "ltq": "5",
            "cp": 1309.85
          },
          "marketLevel": {
            "bidAskQuote": [
              {
                "bidQ": "817",
                "bidP": 1313.65,
                "askQ": "555",
                "askP": 1313.7
              },
              {
                "bidQ": "366",
                "bidP": 1313.6,
                "askQ": "664",
                "askP": 1313.75
              },
              {
                "bidQ": "241",
                "bidP": 1313.55,
                "askQ": "701",
                "askP": 1313.85
              },
              {
                "bidQ": "269",
                "bidP": 1313.5,
                "askQ": "1",
                "askP": 1313.9
              },
              {
                "bidQ": "383",
                "bidP": 1313.4,
                "askQ": "159",
                "askP": 1313.95
              }
            ]
          },
          "optionGreeks": {},
          "marketOHLC": {
            "ohlc": [
              {
                "interval": "1d",
                "open": 1305.6,
                "high": 1316.2,
                "low": 1302.15,
                "close": 1313.65,
                "vol": "7792081",
                "ts": "1742322600000"
              },
              {
                "interval": "I1",
                "open": 1312.75,
                "high": 1313.45,
                "low": 1312.6,
                "close": 1313.1,
                "vol": "45682",
                "ts": "1742373900000"
              }
            ]
          },
          "atp": 1310.68,
          "vtt": "7792081",
          "tbq": 358551.0,
          "tsq": 419777.0
        }
      },
      "requestMode": "full_d5"
    }
  },
  "currentTs": "1742374001020"
}
# --------------------------------------------------