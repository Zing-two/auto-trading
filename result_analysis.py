def show_top_results(filename: str, count: int):
    result = []
    with open(filename, "r") as f:
        for line in f:
            data = line.replace("\n", "").replace(" ", "").split(",")
            result.append([data[0], float(data[1]), float(data[-1])])
    result.sort(key=lambda x: x[2], reverse=True)
    for i in result[:count]:
        print(i)

if __name__ == "__main__":
    filename = "trading_log/buy_rsi_below_15_sell_rsi_above_85_BTCUSDT_result.txt"
    # filename = "trading_log/rsi_below_15_BTCUSDT_result.txt"
    count = 10
    show_top_results(filename, count)
