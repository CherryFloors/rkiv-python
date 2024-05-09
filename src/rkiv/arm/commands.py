# import json
# from urllib.request import urlopen

import click

# from pydvdid import compute  # type: ignore


@click.command()
# @click.option("-d", "--dev", required=True)
def arm():
    """arm"""

    # get_disc_type
    # get_disc_info
    # get_disc_title

    click.secho("Automatic Ripping Machine", fg="green")
    # click.echo(f"Searching for match to {dev}")
    # crc64 = compute(dev)
    # click.echo(f"CRC64: {crc64}")
    # urlstring = f"https://1337server.pythonanywhere.com/api/v1/?mode=s&crc64={crc64}"
    # dvd_xml = urlopen(urlstring).read()
    # print(json.dumps(json.loads(dvd_xml), indent=4))
