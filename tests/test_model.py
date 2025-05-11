"""Test the data model."""

import unittest

from curies import Converter

from obographs import GraphDocument, read
from obographs.model import get_id_to_edges, get_id_to_node
from obographs.standardized import StandardizedGraph, StandardizedGraphDocument


def read_example(name: str) -> GraphDocument:
    """Read the example OBO Graph JSON document."""
    url = f"https://raw.githubusercontent.com/geneontology/obographs/refs/heads/master/examples/{name}.json"
    return read(url, squeeze=False)


class TestModel(unittest.TestCase):
    """Test the data model."""

    def test_abox(self) -> None:
        """Test the ABox example."""
        graphs = read_example("abox")
        self.assertEqual(1, len(graphs.graphs))
        graph = graphs.graphs[0]
        self.assertEqual("http://purl.obolibrary.org/obo/T", graph.id)

        id_to_node = get_id_to_node(graph)
        self.assertIn("http://purl.obolibrary.org/obo/T/Female", id_to_node)

        node = id_to_node["http://purl.obolibrary.org/obo/T/Female"]
        self.assertEqual("CLASS", node.type)

        id_to_edges = get_id_to_edges(graph)
        self.assertIn("http://purl.obolibrary.org/obo/T/Female", id_to_edges)
        self.assertIn(
            ("is_a", "http://purl.obolibrary.org/obo/T/Person"),
            id_to_edges["http://purl.obolibrary.org/obo/T/Female"],
        )

        converter = Converter.from_prefix_map(
            {
                "obo": "http://purl.obolibrary.org/obo/",
            }
        )

        standard_graph = StandardizedGraph.from_obograph_raw(graph, converter)
        self.assertEqual("http://purl.obolibrary.org/obo/T", standard_graph.id)

    def test_roundtrip(self) -> None:
        """Test roundtrip."""
        converter = Converter.from_prefix_map(
            {
                "obo": "http://purl.obolibrary.org/obo/",
                "BFO": "http://purl.obolibrary.org/obo/BFO_",
                "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "dc": "http://purl.org/dc/elements/1.1/",
                "dcterms": "http://purl.org/dc/terms/",
                "KEGG": "http://www.kegg.jp/entry/",
                "PMID": "https://pubmed.ncbi.nlm.nih.gov/",
                "Wikipedia": "http://en.wikipedia.org/wiki/",
            }
        )
        self.maxDiff = None
        for example in [
            "abox",
            "basic",
            "hp",
            "nucleus",
            "ro",
            "obsoletion_example",
            "logicalDefinitionTest",
            "hp",
            "equivNoteSetTest",
        ]:
            with self.subTest(example=example):
                graph_document = read_example(example)
                st_graph_document = StandardizedGraphDocument.from_obograph_raw(
                    graph_document,
                    converter,
                    strict=True,
                )
                reconstituted = st_graph_document.to_raw(converter)
                self.assertEqual(
                    graph_document.graphs[0].model_dump(
                        exclude_unset=True, exclude_none=True, exclude_defaults=True
                    ),
                    reconstituted.graphs[0].model_dump(
                        exclude_unset=True, exclude_none=True, exclude_defaults=True
                    ),
                    msg=f"failed on {example}",
                )
