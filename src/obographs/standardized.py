"""Standardize an OBO graph."""

from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Generic, TypeVar

from curies import Converter, Reference, Triple, vocabulary
from pydantic import BaseModel, Field
from typing_extensions import Self

from obographs.model import (
    Definition,
    Edge,
    Graph,
    GraphDocument,
    Meta,
    Node,
    NodeType,
    Property,
    PropertyType,
    Synonym,
    Xref,
)

__all__ = [
    "StandardizedDefinition",
    "StandardizedEdge",
    "StandardizedGraph",
    "StandardizedGraphDocument",
    "StandardizedMeta",
    "StandardizedNode",
    "StandardizedProperty",
    "StandardizedSynonym",
    "StandardizedXref",
]

logger = logging.getLogger(__name__)


def _expand_list(references: list[Reference] | None, converter: Converter) -> list[str] | None:
    if references is None or not references:
        return None
    return [converter.expand_reference(r.pair, strict=True) for r in references]


X = TypeVar("X")


class StandardizedBaseModel(BaseModel, Generic[X]):
    """A standardized property."""

    @classmethod
    @abstractmethod
    def from_obograph_raw(cls, obj: X, converter: Converter) -> Self | None:
        """Instantiate by standardizing a raw OBO Graph object."""
        raise NotImplementedError

    @abstractmethod
    def to_raw(self, converter: Converter) -> X:
        """Create a raw object."""
        raise NotImplementedError


class StandardizedProperty(StandardizedBaseModel[Property]):
    """A standardized property."""

    predicate: Reference
    value: Reference | str = Field(
        ..., description="Parsed into a Reference if a CURIE or IRI, or a string if it's a literal"
    )
    xrefs: list[Reference] | None = None
    meta: StandardizedMeta | None = None

    @classmethod
    def from_obograph_raw(cls, prop: Property, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        if not prop.val or not prop.pred:
            raise ValueError
        value: Reference | str | None
        if not prop.val.startswith("http://") and not prop.val.startswith("https"):
            value = _curie_or_uri_to_ref(prop.val, converter)
        else:
            value = prop.val
        if value is None:
            raise ValueError
        return cls(
            predicate=_curie_or_uri_to_ref(prop.pred, converter),
            value=value,
        )

    def to_raw(self, converter: Converter) -> Property:
        """Create a raw object."""
        return Property(
            pred=converter.expand_reference(self.predicate.pair),
            val=self.value,
            xrefs=_expand_list(self.xrefs, converter),
            meta=self.meta.to_raw(converter) if self.meta is not None else None,
        )


class StandardizedDefinition(StandardizedBaseModel[Definition]):
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

    def to_raw(self, converter: Converter) -> Definition:
        """Create a raw object."""
        return Definition(
            val=self.value,
            xrefs=_expand_list(self.xrefs, converter),
        )


class StandardizedXref(StandardizedBaseModel[Xref]):
    """A standardized database cross-reference."""

    reference: Reference

    @classmethod
    def from_obograph_raw(cls, xref: Xref, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(reference=_curie_or_uri_to_ref(xref.val, converter))

    def to_raw(self, converter: Converter) -> Xref:
        """Create a raw object."""
        return Xref(val=converter.expand_reference(self.reference.pair))


class StandardizedSynonym(StandardizedBaseModel[Synonym]):
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

    def to_raw(self, converter: Converter) -> Synonym:
        """Create a raw object."""
        return Synonym(
            val=self.text,
            predicate=converter.expand_reference(self.predicate.pair),
            synonymType=converter.expand_reference(self.type.pair)
            if self.type is not None
            else None,
            xrefs=_expand_list(self.xrefs, converter),
        )


class StandardizedMeta(StandardizedBaseModel[Meta]):
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
    def from_obograph_raw(  # noqa:C901
        cls, meta: Meta | None, converter: Converter, flag: str = ""
    ) -> Self | None:
        """Instantiate by standardizing a raw OBO Graph object."""
        if meta is None:
            return None

        xrefs = []
        for raw_xref in meta.xrefs or []:
            if raw_xref.val:
                try:
                    st_xref = StandardizedXref.from_obograph_raw(raw_xref, converter)
                except ValueError:
                    logger.debug("[%s] failed to standardize xref: %s", flag, raw_xref)
                else:
                    xrefs.append(st_xref)

        synonyms = []
        for raw_synonym in meta.synonyms or []:
            if raw_synonym.val:
                try:
                    s = StandardizedSynonym.from_obograph_raw(raw_synonym, converter)
                except ValueError:
                    logger.debug("[%s] failed to standardize synonym: %s", flag, raw_synonym)
                else:
                    synonyms.append(s)

        props = []
        for raw_prop in meta.basicPropertyValues or []:
            if raw_prop.val and raw_prop.pred:
                try:
                    prop = StandardizedProperty.from_obograph_raw(raw_prop, converter)
                except ValueError:
                    logger.debug("[%s] failed to standardize property: %s", flag, raw_prop)
                else:
                    props.append(prop)

        return cls(
            definition=StandardizedDefinition.from_obograph_raw(meta.definition, converter),
            subsets=[_curie_or_uri_to_ref(subset, converter) for subset in meta.subsets]
            if meta.subsets
            else None,
            xrefs=xrefs or None,
            synonyms=synonyms or None,
            comments=meta.comments,
            version=meta.version,
            deprecated=meta.deprecated,
            properties=props or None,
        )

    def to_raw(self, converter: Converter) -> Meta:
        """Create a raw object."""
        return Meta(
            definition=self.definition.to_raw(converter)
            if self.definition and self.definition.value
            else None,
            subsets=_expand_list(self.subsets, converter),
            xrefs=_expand_list(self.xrefs, converter),
            synonyms=[s.to_raw(converter) for s in self.synonyms] if self.synonyms else None,
            comments=self.comments,
            version=self.version,  # TODO might need some kind of expansion?
            deprecated=self.deprecated,
            basicPropertyValues=[p.to_raw(converter) for p in self.properties]
            if self.properties
            else None,
        )


class StandardizedNode(StandardizedBaseModel[Node]):
    """A standardized node."""

    reference: Reference
    label: str | None = Field(None)
    meta: StandardizedMeta | None = None
    type: NodeType | None = Field(None, description="Type of node")
    property_type: PropertyType | None = Field(
        None, description="Type of property, if the node type is a property"
    )

    @classmethod
    def from_obograph_raw(cls, node: Node, converter: Converter) -> Self | None:
        """Instantiate by standardizing a raw OBO Graph object."""
        reference = _curie_or_uri_to_ref(node.id, converter)
        if reference is None:
            logger.warning("failed to parse node's ID %s", node.id)
            return None
        return cls(
            reference=reference,
            label=node.lbl,
            meta=StandardizedMeta.from_obograph_raw(node.meta, converter, flag=reference.curie),
            type=node.type,
            property_type=node.propertyType,
        )

    def to_raw(self, converter: Converter) -> Node:
        """Create a raw object."""
        return Node(
            id=converter.expand_reference(self.reference.pair),
            lbl=self.label,
            meta=self.meta.to_raw(converter) if self.meta is not None else None,
            type=self.type,
            propertyType=self.property_type,
        )


class StandardizedEdge(Triple, StandardizedBaseModel[Edge]):
    """A standardized edge."""

    subject: Reference
    predicate: Reference
    object: Reference
    meta: StandardizedMeta | None = None

    @classmethod
    def from_obograph_raw(cls, edge: Edge, converter: Converter) -> Self | None:
        """Instantiate by standardizing a raw OBO Graph object."""
        subject = _curie_or_uri_to_ref(edge.sub, converter)
        if not subject:
            logger.warning("failed to parse edge's subject %s", edge.sub)
            return None
        predicate = _curie_or_uri_to_ref(edge.pred, converter)
        if not predicate:
            logger.warning("failed to parse edge's predicate %s", edge.pred)
            return None
        obj = _curie_or_uri_to_ref(edge.obj, converter)
        if not obj:
            logger.warning("failed to parse edge's object %s", edge.obj)
            return None
        return cls(
            subject=subject,
            predicate=predicate,
            object=obj,
            meta=StandardizedMeta.from_obograph_raw(
                edge.meta, converter, flag=f"{subject.curie} {predicate.curie} {obj.curie}"
            ),
        )

    def to_raw(self, converter: Converter) -> Edge:
        """Create a raw object."""
        if self.predicate in REVERSE_BUILTINS:
            predicate = REVERSE_BUILTINS[self.predicate]
        else:
            predicate = converter.expand_reference(self.predicate.pair, strict=True)

        return Edge(
            sub=converter.expand_reference(self.subject.pair),
            pred=predicate,
            obj=converter.expand_reference(self.object.pair),
            meta=self.meta.to_raw(converter) if self.meta is not None else None,
        )


class StandardizedGraph(StandardizedBaseModel[Graph]):
    """A standardized graph."""

    id: str | None = None
    meta: StandardizedMeta | None = None
    nodes: list[StandardizedNode] = Field(default_factory=list)
    edges: list[StandardizedEdge] = Field(default_factory=list)

    # TODO other bits
    # equivalentNodesSets
    # logicalDefinitionAxioms
    # domainRangeAxioms
    # propertyChainAxioms

    @classmethod
    def from_obograph_raw(cls, graph: Graph, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph object."""
        return cls(
            id=graph.id,
            meta=StandardizedMeta.from_obograph_raw(graph.meta, converter, flag=graph.id or ""),
            nodes=[
                s_node
                for node in graph.nodes
                if (s_node := StandardizedNode.from_obograph_raw(node, converter))
            ],
            edges=[
                s_edge
                for edge in graph.edges
                if (s_edge := StandardizedEdge.from_obograph_raw(edge, converter))
            ],
        )

    def to_raw(self, converter: Converter) -> Graph:
        """Create a raw object."""
        return Graph(
            id=...,
            meta=self.meta.to_raw(converter) if self.meta is not None else None,
            nodes=[node.to_raw(converter) for node in self.nodes],
            edges=[edge.to_raw(converter) for edge in self.edges],
            # TODO other bits
        )

    def _get_property(self, predicate: Reference) -> str | Reference | None:
        if self.meta is None:
            return None

        for p in self.meta.properties or []:
            if p.predicate == predicate:
                return p.value

        return None

    @property
    def name(self) -> str | None:
        """Look up the name of the graph."""
        r = self._get_property(Reference(prefix="dcterms", identifier="title"))
        if isinstance(r, Reference):
            raise TypeError
        return r


class StandardizedGraphDocument(StandardizedBaseModel[GraphDocument]):
    """A standardized graph document."""

    graphs: list[StandardizedGraph]
    meta: StandardizedMeta | None = None

    @classmethod
    def from_obograph_raw(cls, graph_document: GraphDocument, converter: Converter) -> Self:
        """Instantiate by standardizing a raw OBO Graph Document object."""
        return cls(
            graphs=[
                StandardizedGraph.from_obograph_raw(graph, converter)
                for graph in graph_document.graphs
            ],
            meta=StandardizedMeta.from_obograph_raw(graph_document.meta, converter),
        )

    def to_raw(self, converter: Converter) -> GraphDocument:
        """Create a raw object."""
        return GraphDocument(
            graphs=[graph.to_raw(converter) for graph in self.graphs],
            meta=self.meta.to_raw(converter) if self.meta is not None else None,
        )


def _parse_list(curie_or_uris: list[str] | None, converter: Converter) -> list[Reference] | None:
    if not curie_or_uris:
        return None
    return [
        reference
        for curie_or_uri in curie_or_uris
        if (reference := _curie_or_uri_to_ref(curie_or_uri, converter))
    ]


#: defined in https://github.com/geneontology/obographs/blob/6676b10a5cce04707d75b9dd46fa08de70322b0b/obographs-owlapi/src/main/java/org/geneontology/obographs/owlapi/FromOwl.java#L36-L39
#: this list is complete.
BUILTINS = {
    "is_a": vocabulary.is_a,
    "subPropertyOf": vocabulary.subproperty_of,
    "type": vocabulary.rdf_type,
    "inverseOf": Reference(prefix="owl", identifier="inverseOf"),
}

REVERSE_BUILTINS = {v: k for k, v in BUILTINS.items()}


def _curie_or_uri_to_ref(s: str, converter: Converter) -> Reference | None:
    if s in BUILTINS:
        return BUILTINS[s]
    reference_tuple = converter.parse(s, strict=False)
    if reference_tuple is not None:
        return reference_tuple.to_pydantic()
    return None
