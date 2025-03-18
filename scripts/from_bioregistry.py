# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "bioregistry",
#     "click",
#     "more_click",
#     "obographs",
#     "tqdm",
# ]
#
# [tool.uv.sources]
# obographs = { path = "..", editable = true }
# bioregistry = { path = "../../bioregistry", editable = true }
# ///

"""Parse all OBO Graphs available in the Bioregistry."""

import traceback

import bioregistry
import click
import requests
from curies import Converter
from more_click import verbose_option
from tqdm import tqdm

import obographs

SKIPS = {
    "ncbitaxon",
    "pcl",
    "rbo",
}


@click.command()
@verbose_option
def main() -> None:
    """Parse all OBO Graphs available in the Bioregistry."""
    click.echo("Getting converter")
    converter: Converter = bioregistry.get_converter(include_prefixes=True)
    converter.add_prefix("http", "http://")
    converter.add_prefix("https", "https://")
    click.echo("Indexing resources")
    resources = [
        (resource, url)
        for resource in bioregistry.resources()
        if resource.prefix not in SKIPS
        and (url := resource.get_download_obograph()) is not None
        and resource.prefix > "ncbitaxon"
    ]
    for resource, url in tqdm(
        resources, desc="Parsing OBO Graph JSON in Bioregistry", unit="ontology"
    ):
        tqdm.write(f"[{resource.prefix}] Parsing {resource.get_name()}")
        try:
            graph_raw = obographs.read(url)
        except requests.exceptions.JSONDecodeError:
            tqdm.write(
                click.style(f"[{resource.prefix}] failed to decode JSON from {url}", fg="red")
            )
            continue
        except Exception as e:
            tqdm.write(
                click.style(f"[{resource.prefix}] failed to read from {url} - {e}", fg="red")
            )
            traceback.print_exception(e)
            continue
        try:
            graph = graph_raw.standardize(converter)
        except Exception as e:
            tqdm.write(click.style(f"[{resource.prefix}] failed to standardize - {e}", fg="red"))
            continue
        tqdm.write(
            f"[{resource.prefix}] Done with #nodes={len(graph.nodes)} #edges={len(graph.edges)}"
        )


if __name__ == "__main__":
    main()
