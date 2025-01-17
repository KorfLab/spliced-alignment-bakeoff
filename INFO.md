INFO: Spliced Alignment Benchmarking Resource
=============================================

## Flattened Transcript Format (.ftx) ##

This project uses a custom file format to serialize gene structure annotation
into a single token for embedding in FASTA/FASTQ identifiers. It is not
intended to be used outside this study.

- file extension: `.ftx` (not an official file extension)
- field delimiter: `|`
- 5 fields
- no spaces in fields 1-4

1. chromosome identifier
2. name of gene/transcript/read/whatever
3. strand indicator `+` or `-`
4. exon structure:
	- hyphen separated coordinates
	- comma separated exons
	- must be sorted left to right, low to high
	- numbers are 1-based
5. information: optional extra free text

Example: Plus-strand transcript with introns at 201-299 and 401-499 and no
extra information.

```
chr1|gene-1|+|100-200,300-400,500-600|
```

Example: Minus-strand transcript with some extra info.

```
chr2|gene-2|-|100-200,300-400,500-600|extra free text
```

Example: The information field can contain another ftx. This is used within
SABR to attach a genomic source to all of its alignments (an aligner may
provide more than one alignment). A `~` is often used as a delimiter between
ftx elements.

```
chr1|gene-1|+|100-200,300-400,500-600|~chr1|gene-1|+|100-200,300-400,500-600|
```

## Synthetic Genomes & Reads ##

The `genome-simulator.py` program creates a 3-exon gene whose middle exon has
variable length. A text-glyph is shown below. By default, all introns follow
the GT-AG rule.

```
~~~[exon]--intron--[var.exon]--intron--[exon]~~~
```

Passing the `--double` flag creates genes on both strands and the
`--noncanonical` flag creates introns with additional splice sites: GC-AG,
AT-AC, and AA-TT (AA-TT is used to represent _other_ and not an acutal splice
site).

The `read-simulator.py` program generates reads along the entire length of a
gene's mRNA. The `--double` flag creates reads from both strands.

```
[exon][var.exon][exon]
------ ------ ------
 ------ ------ ------
  ------ ------ ------
   ------ ------
    ------ ------
     ------ ------
      ------ ------
```
