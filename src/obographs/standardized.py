"""Standardize an OBO graph."""

from __future__ import annotations

from curies import Converter, Reference
from pydantic import BaseModel, Field
from typing_extensions import Self

from obographs.model import Definition, Edge, Graph, Meta, Node, NodeType, Property, Synonym, Xref

__all__ = [
    "StandardizedDefinition",
    "StandardizedEdge",
    "StandardizedGraph",
    "StandardizedMeta",
    "StandardizedNode",
    "StandardizedXref",
]


class StandardizedProperty(BaseModel):
    """A standardized property."""

    predicate: Reference
    value: Reference
    xrefs: list[Reference] | None = None
    meta: StandardizedMeta | None = None

    @classmethod
    def from_obograph_raw(cls, prop: Property, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(
            predicate=_curie_or_uri_to_ref(prop.pred, converter),
            value=_curie_or_uri_to_ref(prop.val, converter),
        )


class StandardizedDefinition(BaseModel):
    """A standardized definition."""

    value: str | None = Field(default=None)
    xrefs: list[Reference] | None = Field(default=None)

    @classmethod
    def from_obograph_raw(cls, definition: Definition | None, converter: Converter) -> Self | None:
        """Instantiate by standardizing a raw OBO Graph object."""
        if definition is None:
            return None
        return cls(
            value=definition.val,
            xrefs=_parse_list(definition.xrefs, converter),
        )


class StandardizedXref(BaseModel):
    """A standardized database cross-reference."""

    reference: Reference

    @classmethod
    def from_obograph_raw(cls, xref: Xref, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(reference=_curie_or_uri_to_ref(xref.val, converter))


class StandardizedSynonym(BaseModel):
    """A standardized synonym."""

    text: str
    predicate: Reference
    type: Reference | None = None
    xrefs: list[Reference] | None = None

    @classmethod
    def from_obograph_raw(cls, synonym: Synonym, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(
            text=synonym.val,
            predicate=Reference(prefix="oboInOwl", identifier=synonym.pred),
            type=synonym.synonymType and _curie_or_uri_to_ref(synonym.synonymType, converter),
            xrefs=_parse_list(synonym.xrefs, converter),
        )


class StandardizedMeta(BaseModel):
    """A standardized meta object."""

    definition: StandardizedDefinition | None
    subsets: list[Reference] | None = None
    xrefs: list[StandardizedXref] | None = None
    synonyms: list[StandardizedSynonym] | None = None
    comments: list[str] | None = None
    deprecated: bool = False
    version: str | None = None
    properties: list[StandardizedProperty] | None = None

    @classmethod
    def from_obograph_raw(cls, meta: Meta | None, converter: Converter) -> Self | None:
        """Instantiate by standardizing a raw OBO Graph object."""
        if meta is None:
            return None
        return cls(
            definition=StandardizedDefinition.from_obograph_raw(meta.definition, converter),
            subsets=[_curie_or_uri_to_ref(subset, converter) for subset in meta.subsets]
            if meta.subsets
            else None,
            xrefs=[StandardizedXref.from_obograph_raw(xref, converter) for xref in meta.xrefs]
            if meta.xrefs
            else None,
            synonyms=[
                StandardizedSynonym.from_obograph_raw(synonym, converter)
                for synonym in meta.synonyms
            ]
            if meta.synonyms
            else None,
            comments=meta.comments,
            version=meta.version,
            deprecated=meta.deprecated,
            properties=[
                StandardizedProperty.from_obograph_raw(p, converter)
                for p in meta.basicPropertyValues
            ]
            if meta.basicPropertyValues
            else None,
        )


class StandardizedNode(BaseModel):
    """A standardized node."""

    reference: Reference
    label: str | None = Field(None)
    meta: StandardizedMeta | None = None
    type: NodeType = Field(..., description="Type of node")

    @classmethod
    def from_obograph_raw(cls, node: Node, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(
            reference=_curie_or_uri_to_ref(node.id, converter),
            label=node.lbl,
            meta=StandardizedMeta.from_obograph_raw(node.meta, converter),
            type=node.type,
        )


class StandardizedEdge(BaseModel):
    """A standardized edge."""

    subject: Reference
    predicate: Reference
    object: Reference
    meta: StandardizedMeta | None = None

    @classmethod
    def from_obograph_raw(cls, node: Edge, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(
            subject=_curie_or_uri_to_ref(node.sub, converter),
            predicate=_curie_or_uri_to_ref(node.pred, converter),
            object=_curie_or_uri_to_ref(node.obj, converter),
            meta=StandardizedMeta.from_obograph_raw(node.meta, converter),
        )


class StandardizedGraph(BaseModel):
    """A standardized graph."""

    id: str | None = None
    meta: StandardizedMeta | None = None
    nodes: list[StandardizedNode] = Field(default_factory=list)
    edges: list[StandardizedEdge] = Field(default_factory=list)

    # TODO other bits

    @classmethod
    def from_obograph_raw(cls, graph: Graph, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(
            id=graph.id,
            meta=StandardizedMeta.from_obograph_raw(graph.meta, converter),
            nodes=[StandardizedNode.from_obograph_raw(node, converter) for node in graph.nodes],
            edges=[StandardizedEdge.from_obograph_raw(edge, converter) for edge in graph.edges],
        )


def _parse_list(ss: list[str] | None, converter: Converter) -> list[Reference] | None:
    if not ss:
        return None
    return [_curie_or_uri_to_ref(x, converter) for x in ss]


#: defined in https://github.com/geneontology/obographs/blob/6676b10a5cce04707d75b9dd46fa08de70322b0b/obographs-owlapi/src/main/java/org/geneontology/obographs/owlapi/FromOwl.java#L36-L39
BUILTINS = {
    "is_a": Reference(prefix="rdfs", identifier="subClassOf"),
    "subPropertyOf": Reference(prefix="rdfs", identifier="subPropertyOf"),
    "type": Reference(prefix="rdf", identifier="type"),
    "inverseOf": Reference(prefix="owl", identifier="inverseOf"),
}


def _curie_or_uri_to_ref(s: str, converter: Converter) -> Reference:
    if s in BUILTINS:
        return BUILTINS[s]
    if converter.is_uri(s):
        p, o = converter.parse_uri(s)
        return Reference(prefix=p, identifier=o)
    elif converter.is_curie(s):
        pass
    raise ValueError(f"can't parse string: {s}")
