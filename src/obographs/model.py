"""Data structures for representing OBO Graphs.

.. seealso::

    - the defining repository https://github.com/geneontology/obographs
    - the JSON schema https://github.com/geneontology/obographs/blob/master/schema/obographs-schema.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal, TypeAlias
from collections import defaultdict

from pydantic import BaseModel, Field

__all__ = [
    "Definition",
    "Edge",
    "Graph",
    "GraphDocument",
    "Meta",
    "Node",
    "Property",
    "Synonym",
    "Xref",
    "read",
]

logger = logging.getLogger(__name__)

OBO_URI_PREFIX = "http://purl.obolibrary.org/obo/"
OBO_URI_PREFIX_LEN = len(OBO_URI_PREFIX)

SynonymPredicate: TypeAlias = Literal[
    "hasExactSynonym",
    "hasBroadSynonym",
    "hasNarrowSynonym",
    "hasRelatedSynonym",
]
NodeType: TypeAlias = Literal["CLASS", "PROPERTY", "INDIVIDUAL"]

#: A mapping from OBO flat file format internal synonym types to OBO in OWL vocabulary
#: identifiers. See https://owlcollab.github.io/oboformat/doc/GO.format.obo-1_4.html
OBO_SYNONYM_TO_OIO: dict[str, SynonymPredicate] = {
    "EXACT": "hasExactSynonym",
    "BROAD": "hasBroadSynonym",
    "NARROW": "hasNarrowSynonym",
    "RELATED": "hasRelatedSynonym",
}


class Property(BaseModel):
    """Represent a property inside a metadata element."""

    pred: str = Field(...)
    val: str = Field(
        ...,
    )


class Definition(BaseModel):
    """Represents a definition for a node."""

    val: str | None = Field(default=None)
    xrefs: list[str] | None = Field(default=None)  # Just a list of CURIEs/IRIs


class Xref(BaseModel):
    """Represents a cross-reference."""

    val: str = Field(...)


class Synonym(BaseModel):
    """Represents a synonym inside an object meta."""

    val: str | None = Field(default=None)
    pred: str = Field(default="hasExactSynonym")
    synonymType: str | None = Field(examples=["OMO:0003000"])  # noqa:N815
    xrefs: list[str] = Field(
        default_factory=list,
        description="A list of CURIEs/IRIs for provenance for the synonym",
    )


class Meta(BaseModel):
    """Represents the metadata about a node or ontology."""

    definition: Definition | None = None
    subsets: list[str] | None = None
    xrefs: list[Xref] | None = None
    synonyms: list[Synonym] | None = None
    comments: list[str] | None = None
    version: str | None = None
    basicPropertyValues: list[Property] | None = Field(None)  # noqa:N815
    deprecated: bool = False


class Edge(BaseModel):
    """Represents an edge in an OBO Graph."""

    sub: str = Field(..., examples=["http://purl.obolibrary.org/obo/CHEBI_99998"])
    pred: str = Field(..., examples=["is_a"])
    obj: str = Field(..., examples=["http://purl.obolibrary.org/obo/CHEBI_24995"])
    meta: Meta | None = None


class Node(BaseModel):
    """Represents a node in an OBO Graph."""

    id: str = Field(..., description="The IRI for the node")
    lbl: str | None = Field(None, description="The name of the node")
    meta: Meta | None = None
    type: NodeType = Field(..., description="Type of node")


class Graph(BaseModel):
    """A graph corresponds to an ontology."""

    id: str | None = None
    meta: Meta | None = None
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    equivalentNodesSets: list[Any] = Field(default_factory=list)  # noqa:N815
    logicalDefinitionAxioms: list[Any] = Field(default_factory=list)  # noqa:N815
    domainRangeAxioms: list[Any] = Field(default_factory=list)  # noqa:N815
    propertyChainAxioms: list[Any] = Field(default_factory=list)  # noqa:N815


class GraphDocument(BaseModel):
    """Represents a list of OBO graphs."""

    graphs: list[Graph]


def get_id_to_node(graph: Graph) -> dict[str, Node]:
    """Get a dictionary from node ID to nodes."""
    return {node.id: node for node in graph.nodes or []}


def get_id_to_edges(graph: Graph) -> dict[str, list[tuple[str, str]]]:
    """Get a dictionary from node ID to nodes."""
    dd = defaultdict(set)
    for edge in graph.edges or []:
        dd[edge.sub].add((edge.pred, edge.obj))
    return {node_id: list(predicate_object_pairs) for node_id, predicate_object_pairs in dd.items()}


def read(source: str, *, timeout: int | float | None = None) -> GraphDocument:
    """Read an OBO Graph document."""
    if (isinstance(source, str) and source.startswith("https://")) or source.startswith("http://"):
        import requests

        if source.endswith(".gz"):
            raise NotImplementedError
        else:
            res = requests.get(source, timeout=timeout)
            res_json = res.json()
            rv = GraphDocument.model_validate(res_json)
            return rv

    if isinstance(source, str | Path):
        path = Path(source).expanduser().resolve()
        if path.is_file():
            if path.suffix.endswith(".gz"):
                raise NotImplementedError
            else:
                with path.open() as file:
                    return GraphDocument.model_validate(json.load(file))
    raise TypeError(f"Unhandled source: {source}")
