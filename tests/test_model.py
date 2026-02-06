"""Test the data model."""

import tempfile
import unittest
from pathlib import Path

from curies import (
    Converter,
    PostprocessingRewrites,
    PreprocessingBlocklists,
    PreprocessingConverter,
    PreprocessingRewrites,
    PreprocessingRules,
)
from pystow.utils import download

from obographs import GraphDocument, read
from obographs.model import get_id_to_edges, get_id_to_node
from obographs.standardized import StandardizedGraph, StandardizedGraphDocument


def read_example(name: str, direct: bool = True) -> GraphDocument:
    """Read the example OBO Graph JSON document."""
    url = f"https://raw.githubusercontent.com/geneontology/obographs/refs/heads/master/examples/{name}.json"
    if direct:
        return read(url, squeeze=False)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir).joinpath(f"{name}.json")
        download(url=url, path=path)
        return read(path, squeeze=False)


SKIP_BECAUSE_DATA = unittest.skip(reason="test is failing for unrelated data reasons")

converter_ = Converter.from_prefix_map(
    {
        "obo": "http://purl.obolibrary.org/obo/",
        "BFO": "http://purl.obolibrary.org/obo/BFO_",
        "NCIT": "http://purl.obolibrary.org/obo/NCIT_",
        "SO": "http://purl.obolibrary.org/obo/SO_",
        "MI": "http://purl.obolibrary.org/obo/MI_",
        "ECO": "http://purl.obolibrary.org/obo/ECO_",
        "oboInOwl": "http://www.geneontology.org/formats/oboInOwl#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "dc": "http://purl.org/dc/elements/1.1/",
        "dcterms": "http://purl.org/dc/terms/",
        "KEGG": "http://www.kegg.jp/entry/",
        "PMID": "https://pubmed.ncbi.nlm.nih.gov/",
        "Wikipedia": "http://en.wikipedia.org/wiki/",
        "foaf": "http://xmlns.com/foaf/0.1/",
        "owl": "http://www.w3.org/2002/07/owl#",
        "MESH": "http://id.nlm.nih.gov/mesh/",
        "cito": "http://purl.org/spar/cito/",
        "bioregistry": "https://bioregistry.io/bioregistry:",
        "Orphanet": "http://www.orpha.net/ORDO/Orphanet_",
        "sao": "http://uri.neuinfo.org/nif/nifstd/sao",
        "doi": "http://dx.doi.org/",
        "SCTID": "http://snomed.info/id/",
        "UMLS": "https://uts.nlm.nih.gov/uts/umls/concept/",
        "MedDRA": "http://bioportal.bioontology.org/ontologies/MEDDRA?p=classes&conceptid=",
        "reaxys": "https://bioregistry.io/reaxys:",
        "MetaCyc": "https://metacyc.org/compound?orgid=META&id=",
        "ISBN": "https://isbnsearch.org/isbn/",
        "nlx.sub": "http://uri.neuinfo.org/nif/nifstd/nlx_subcell_",
        "CAS": "https://commonchemistry.cas.org/detail?cas_rn=",
        "emedicine": "http://emedicine.medscape.com/article/",
    }
)
converter_.add_prefix(
    "reaxys", "https://bioregistry.io/reaxys:", prefix_synonyms=["Beilstein", "Reaxys"], merge=True
)
converter_.add_prefix("wikipedia", "url:http://en.wikipedia.org/wiki/")
converter_.add_prefix("pubmed", "url:http://www.ncbi.nlm.nih.gov/pubmed/")

converter = PreprocessingConverter.from_converter(
    converter_,
    rules=PreprocessingRules(
        rewrites=PreprocessingRewrites(
            full={
                "SO:similar_to": "obo:so#similar_to",
                "ChEBI": "bioregistry:chebi",
                "UniProt": "bioregistry:uniprot",
                "KEGG_COMPOUND": "bioregistry:kegg.compound",
                "RO_proposed_relation:homologous_to": "RO:0002320",
                "TAO:homologous_to": "RO:0002320",
            },
            prefix={
                "url:http:": "http:",
                "NIF_Subcellular:sao-": "sao:",
                "NIF_Subcellular:sao": "sao:",
                "NIF_Subcellular:nlx_subcell_": "nlx.sub:",
            },
        ),
        postprocessing=PostprocessingRewrites(
            suffix={
                "emedicine": ["-overview", "-overview?form=fpf"],
            }
        ),
        blocklists=PreprocessingBlocklists(
            full=[
                "IUPAC",
                "BGEE:curator",
                "GOC:go_curators",
                "GOC:mah",
                "GOC:jl",
                "MeSH:Synteny",
            ],
        ),
    ),
)


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

        standard_graph = StandardizedGraph.from_obograph_raw(graph, converter)
        self.assertEqual("http://purl.obolibrary.org/obo/T", standard_graph.id)

    def test_abox_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("abox", direct=False)
        self.assert_example("abox", direct=True)

    def test_basic_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("basic")

    @SKIP_BECAUSE_DATA
    def test_hp_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("hp")

    @SKIP_BECAUSE_DATA
    def test_nucleus_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("nucleus")

    @SKIP_BECAUSE_DATA
    def test_ro_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("ro")

    def test_obsoletion_example_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("obsoletion_example")

    def test_logical_definition_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("logicalDefinitionTest")

    @SKIP_BECAUSE_DATA
    def test_equivalent_node_roundtrip(self) -> None:
        """Test the example can go through a roundtrip."""
        self.assert_example("equivNodeSetTest")

    def assert_example(self, example: str, *, direct: bool = True) -> None:
        """Assert that the example can go a round-trip."""
        graph_document = read_example(example, direct=direct)
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
