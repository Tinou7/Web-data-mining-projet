# Knowledge Base Statistics

## Initial Graph (`initial_graph.ttl`)
| Metric | Value |
|--------|-------|
| Triplets | 29,336 |
| Entities | 9,937 |
| Relations | 11 |

## Alignment (`alignment.ttl`)
| Metric | Value |
|--------|-------|
| Entities linked to Wikidata | 545 |
| Predicate alignments | 5 |
| Confidence ≥ 0.99 | ~480 |
| Confidence 0.85–0.99 | ~65 |

## Expanded KB (`expanded.nt`)
| Metric | Value |
|--------|-------|
| **Total triplets** | **141,017** |
| Entities | ~95,426 |
| Relations | 31 |
| Expansion method | 1-hop + 2-hop SPARQL on Wikidata |

## KGE Splits (`data/kge/`)
| Split | Triplets |
|-------|----------|
| train.txt | 114,566 |
| valid.txt | 3,870 |
| test.txt | 3,670 |
| **Total** | **122,106** |

## Volume Requirements (Lab 2)
| Requirement | Target | Achieved |
|-------------|--------|----------|
| Triplets | 50,000–200,000 | 141,017 ✓ |
| Entities | 5,000–30,000 | 95,426 ✓ |
| Relations | 50–200 | 31 ⚠️ |

> Note: 31 relations is below the 50–200 target. This is due to the domain specificity
> of vexillology — flags have fewer relation types than general-purpose KGs.
> The Wikidata expansion used 29 carefully selected properties relevant to the flags domain.

## Ontology Classes
- `flags:Country`
- `flags:Flag`
- `flags:Person`
- `flags:Organization`
- `flags:Date`
- `flags:Color`
- `flags:Symbol`
- `flags:Continent`

## Predicate Alignments
| Private Predicate | Wikidata Property | Label |
|-------------------|-------------------|-------|
| flags:hasFlag | wdt:P41 | flag image |
| flags:locatedIn | wdt:P17 | country |
| flags:adoptedIn | wdt:P571 | inception |
| flags:hasSymbol | wdt:P154 | logo image |
| flags:affiliatedWith | wdt:P361 | part of |
