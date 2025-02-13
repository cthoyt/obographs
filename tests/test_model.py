"""Test the data model."""

import unittest

from obographs import GraphDocument, read
from obographs.model import get_id_to_edges, get_id_to_node


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
