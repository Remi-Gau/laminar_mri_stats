import json
from pathlib import Path
from typing import Any

import gender_guesser.detector as gender
import pandas as pd
import requests
from rich import print

UPDATE = True


def root_dir():
    return Path(__file__).parent


def data_dir():
    return root_dir() / "data"


def paper_listing(load_updated=not UPDATE):
    if load_updated:
        return data_dir() / "paper_listing_updated.tsv"
    return data_dir() / "paper_listing.tsv"


def get_doi_from_link(link: Any):
    if not isinstance(link, str):
        return link
    if link.startswith("https://doi.org/"):
        return link.replace("https://doi.org/", "")
    elif "10." in link:
        doi = link.split("10.")[-1]
        doi = doi.split("/")[:2]
        doi = "10." + "/".join(doi)
        return doi.strip()
    else:
        return link


def query_for_metadata(doi: str) -> dict[str, str]:
    with open("token.txt") as f:
        token = f.read().strip()
    headers = {"authorization": token}
    api_call = f"https://opencitations.net/index/coci/api/v1/metadata/{doi}"
    r = requests.get(api_call, headers=headers)
    if r.status_code == 200:
        return r.json()
    print(f"[red]Error: {r.status_code}[/red]")
    return {}


def paper_listing_df():
    # Read the paper listing file and omit lines 2 to 5
    df = pd.read_csv(paper_listing(), sep="\t", skiprows=[1, 2, 3, 4, 5])

    # sanitize column names
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("(", "")
        .str.replace(")", "")
        .str.replace("?", "")
    )

    # use short names from data dict
    with open(data_dir() / "paper_listing.json", "r") as f:
        data_dict = json.load(f)

    for key in data_dict.keys():
        if data_dict[key].get("long_name") in df.columns:
            if data_dict[key].get("short_name"):
                df.rename(
                    columns={data_dict[key]["long_name"]: data_dict[key]["short_name"]},
                    inplace=True,
                )

    # drop some columns
    for key in data_dict.keys():
        if data_dict[key].get("short_name") in df.columns:
            if data_dict[key].get("drop"):
                df.drop(columns=[data_dict[key]["short_name"]], inplace=True)

    # convert date column to datetime with year only
    df["year"] = pd.to_datetime(df["year"], format="%Y")

    return df


def parse_authors(authors: str):
    if " . " in authors:
        names = authors.split(" . ")
    elif " | " in authors:
        names = authors.split(" | ")
    elif "; " in authors:
        names = authors.split(";")
    else:
        names = authors.split(", ")

    authors = []

    for x in names:
        tokens = x.split(", ")
        # only include words that are all letters or wiht a dot
        tokens = [x.strip() for x in tokens]
        tokens = [x for x in tokens if x.isalpha() or "." in x]
        authors.append(", ".join(tokens))
    return authors


def update_data_frame(df: pd.DataFrame):
    # add doi column to df
    dois = []
    journal_names = []
    authors = []
    citation_count = []

    for x in df.iterrows():
        link = x[1]["link"]
        print(link)

        doi = get_doi_from_link(link)
        print(doi)

        dois.append(doi)

        metadata = query_for_metadata(doi)
        print(metadata)
        if metadata:
            metadata = metadata[0]
            if metadata["source_title"] != "":
                source_title = metadata["source_title"]
            else:
                source_title = x[1]["journal"]
            journal_names.append(source_title)
            authors.append(metadata["author"])
            citation_count.append(metadata["citation_count"])
        else:
            journal_names.append(x[1]["journal"])
            authors.append(x[1]["authors"])
            citation_count.append("n/a")

    df["doi"] = dois
    df["journal"] = journal_names
    df["authors"] = authors
    df["citation_count"] = citation_count

    return df


def get_surname(names):
    tokens = names.split(", ")
    if len(tokens) > 1:
        return tokens[1].split(" ")[0] if "." in tokens[1] else tokens[1]
    else:
        return tokens[0]


def guess_gender(df):

    gender_first_author = []
    gender_last_author = []
    proportion_male_in_authors = []

    for names in df.authors:

        if not isinstance(names, str):
            gender_first_author.append("n/a")
            gender_last_author.append("n/a")
            proportion_male_in_authors.append("n/a")
            continue

        names = parse_authors(names)
        print(names)

        if isinstance(names, list):
            d = gender.Detector()
            guesses = []
            guesses = [d.get_gender(get_surname(x)) for x in names]
            gender_first_author.append(guesses[0])
            gender_last_author.append(guesses[-1])
            if guesses := [x for x in guesses if x != "unknown"]:
                count = sum("male" in x for x in guesses)
                proportion_male_in_authors.append(count / len(guesses))
            else:
                proportion_male_in_authors.append("n/a")

    df["gender_first_author"] = gender_first_author
    df["gender_last_author"] = gender_last_author
    df["proportion_male_in_authors"] = proportion_male_in_authors

    return df


def main():
    df = paper_listing_df()
    print(df.head())
    print(df.columns)

    if UPDATE:
        df = update_data_frame(df)
    df.to_csv(data_dir() / "paper_listing_updated.tsv", index=False, sep="\t")

    print(df.head())
    df = guess_gender(df)

    df.to_csv(data_dir() / "paper_listing_updated.tsv", index=False, sep="\t")


if __name__ == "__main__":
    main()
