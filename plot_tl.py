#!/usr/bin/env python3

from sys import argv, stderr

import pandas as pd
from matplotlib import pyplot as plt

plt.style.use("fivethirtyeight")
plt.rcParams["svg.fonttype"] = "none"
# plt.rcParams["font.family"] = "Noto Sans"
plt.rcParams["font.family"] = "Vazir"


def plot_timeline(chats_addr: str, plot_addr: str, rule: str) -> None:
    def merge_names(df: pd.DataFrame, remaining_name: str, deleting_name: str) -> None:
        df[remaining_name] += df[deleting_name]
        df = df.drop(deleting_name, axis=1)

    df = pd.read_csv(chats_addr)
    df["Date"] = df["Date"].str.replace(r"([0-9]{2})\.([0-9]{2})\.([0-9]{4}) ", r"\3-\2-\1 ", regex=True)
    df.index = pd.to_datetime(df["Date"])
    df["From"] = (df["From"] + " - " + df["Signed By"]).fillna(df["From"])

    df = df.groupby("From").resample(rule).count()["Id"].unstack(level=0).fillna(0)

    print(df.columns)
    print(df)

    df = df.rolling("60D").mean()
    # df = df.cumsum(axis=1)

    # figsize = (8, 4.5)
    figsize = (16, 9)
    ax = df.plot(figsize=figsize)
    ax.set_ylabel("Posts per %s" % rule)
    # plt.grid()
    # plt.savefig(plot_addr)
    plt.show()


def main():
    if len(argv) not in {2, 3, 4}:
        print("usage:\t%s <Chats CSV Path> [rule] [<Chats TimeLine SVG>]" % argv[0], file=stderr)
        exit(2)

    chats_addr = argv[1]
    assert chats_addr.endswith(".csv")
    plot_addr = argv[3] if len(argv) > 3 else chats_addr.replace(".csv", ".tl.svg")
    assert plot_addr.endswith(".svg")
    rule = argv[2] if len(argv) > 2 else "1M"
    print("Resampling Rule:\t%s" % rule)
    plot_timeline(chats_addr, plot_addr, rule)


if __name__ == '__main__':
    main()
