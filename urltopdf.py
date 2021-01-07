import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from urllib.parse import urlparse


def urltopdf(filename, outdir, chrome_bin_path):
    """Scans file for URLs and renders all urls
    as PDF using headless Chrome/Chromium.

    Args:
        filename: File to scan for URLs.
        outdir: Directory for saving the the PDFs.
        chrome_bin_path: Absolute path to Chrome/Chromium bin.
    """
    urls = list()

    print(f"Grepping all urls from {filename}")

    with open(filename) as f:
        for line in f:
            # https://urlregex.com/
            new_urls = re.findall(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", line)
            urls.extend(new_urls)

    if len(urls) == 0:
        print("No urls found.")
        return

    print(f"Found {len(urls)} urls.")

    if not os.path.exists(outdir):
        os.mkdir(outdir)

    metadata_path = os.path.join(outdir, "urltopdf_metadata.json")
    metadata = dict()
    if os.path.exists(metadata_path):
        with open(metadata_path) as mf:
            metadata = json.load(mf)

    stats = dict()
    stats["downloaded"] = []
    stats["cached"] = []
    stats["failed"] = []
    for url in urls:
        # Skip already downloaded urls.
        if url in metadata:
            stats["cached"].append(url)
            continue

        # Remove '/' from the end and take take last part of the url.
        url_target = urlparse(url).path.strip("/").split("/")[-1]
        # Replace all non alphanumeric characters with underscore.
        fname = "".join([ch if ch.isalnum() else "_" for ch in url_target])
        fname += "_"
        # Add a simple hash to prevent filename collisions.
        fname += hashlib.md5(url.encode("utf-8")).hexdigest()
        fname += ".pdf"

        outputfile = os.path.join(outdir, fname)

        print(f"Downloading and converting: {url}")
        success = False
        try:
            cmd = [chrome_bin_path,
                   "--headless",
                   "--run-all-compositor-stages-before-draw",
                   "--disable-gpu",
                   f"--print-to-pdf={outputfile}",
                   f"{url}"]

            output = subprocess.call(cmd)
            print(f"{cmd} out: {output}")
            success = True
        except Exception as e:
            print(f"Error from Chrome: {e}. cmd {cmd}")

        if success:
            # Update metadata if the download succeeded
            metadata[url] = dict()
            metadata[url]["filename"] = fname
            metadata[url]["timestamp"] = datetime.datetime.now().strftime(
                "%d-%m-%Y, %H:%M:%S")
            with open(metadata_path, "w") as mf_out:
                json.dump(metadata, mf_out)
            stats["downloaded"].append(url)
        else:
            stats["failed"].append(url)

    print(f'''Done.
* Downloaded: {len(stats["downloaded"])}
* Cached and not downloaded: {len(stats["cached"])}
* Failed: {stats["failed"]}''')


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: urltopdf.py [filename-containing-urls] [output-dir] [chromium-bin]")
        exit(1)
    urltopdf(sys.argv[1], sys.argv[2], sys.argv[3])
    exit(0)
