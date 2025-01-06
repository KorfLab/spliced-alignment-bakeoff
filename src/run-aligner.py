import argparse
import gzip
import os
import sys
import time

from toolbox import FTX, sam_to_ftx, readfasta

def run(cli):
	cli = '/usr/bin/time -f "BAKEOFF TIME %M %U %S %E" ' + cli
	print(cli, file=sys.stderr)
	os.system(cli)

def needfastq(arg):
	fastq = f'{arg.reads[0:arg.reads.find(".")]}.fq.gz'
	if not os.path.exists(fastq):
		with gzip.open(fastq, 'wt') as fp:
			for name, seq in readfasta(arg.reads):
				print('@', name, file=fp, sep='')
				print(seq, file=fp)
				print('+', file=fp)
				print('J' * len(seq), file=fp)
	return fastq

def needfasta(arg):
	fasta = arg.reads[:-3]
	if not os.path.exists(fasta): os.system(f'gunzip -k {arg.reads}')
	return fasta

def samfile_to_ftxfile(filename, ftxfile):
	with open(ftxfile, 'w') as out:
		for ftx in sam_to_ftx(filename):
			print(ftx, file=out)

def sim4file_to_ftxfile(filename, ftxfile):
	chrom = None
	strand = None
	exons = []
	ref = None
	n = 0
	with open(filename) as fp:
		with open(ftxfile, 'w') as out:
			for line in fp:
				if line.startswith('seq1 ='):
					if chrom is not None:
						ftx = FTX(chrom, str(n), strand, exons, f'~{ref}')
						print(ftx, file=out)
					chrom = None
					strand = None
					exons = []
					ref = line[7:].split(' ')[0][:-1]
					n += 1
					continue
				elif line.startswith('seq2 ='):
					f = line.split()
					chrom = f[2][:-1]
					continue
				f = line.split()
				if len(f) != 4: continue
				beg, end = f[1][1:-1].split('-')
				exons.append((int(beg) -1, int(end) -1))
				st = '+' if f[3] == '->' else '-'
				if strand is None: strand = st
				else: assert(strand == st)
			ftx = FTX(chrom, str(n), strand, exons, f'~{ref}')
			print(ftx, file=out)

#######
# CLI #
#######

programs = ('bbmp', 'blat', 'bow2', 'bwam', 'gem3', 'gmap', 'hst2', 'magi',
	'min2', 'pblt', 'sege', 'star', 'subr', 'top2')
parser = argparse.ArgumentParser( description=f'spliced alignment runner',
	epilog = 'programs: ' + ' '.join(programs))
parser.add_argument('genome', help='genome file in FASTA format')
parser.add_argument('reads', help='reads file in FASTA format')
parser.add_argument('program', help='abbreviation of program name')
parser.add_argument('--accurate', action='store_true',
	help='use parameters optimized for accuracy')
parser.add_argument('--threads', type=int, default=1,
	help='number of threads if changeable [%(default)i]')
parser.add_argument('--debug', action='store_true',
	help='keep temporary files (e.g. SAM)')
arg = parser.parse_args()
if arg.program not in programs: sys.exit(f'unknown program: {arg.program}')
if arg.accurate: sys.exit('--accurate not implemented yet')

###############
# Run Aligner #
###############

out = f'tmp-{arg.program}' # temporary output file
ftx = f'ftx-{arg.program}' # temporary ftx file
t0 = time.time()

if arg.program == 'blat':
	run(f'blat {arg.genome} {arg.reads} {out} -out=sim4')
	sim4file_to_ftxfile(out, ftx)
elif arg.program == 'bbmp':
	if not os.path.exists('ref'): run(f'bbmap.sh ref={arg.genome}')
	run(f'bbmap.sh in={arg.reads} ref={arg.genome} threads={arg.threads} out={out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'bow2':
	if not os.path.exists(f'{arg.genome}.1.bt2'): run(f'bowtie2-build {arg.genome} {arg.genome}')
	fastq = needfastq(arg) # note: requires fastq
	run(f'bowtie2 -x {arg.genome} -U {fastq} -k 5 > {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'bwam':
	if not os.path.exists(f'{arg.genome}.bwt'): run(f'bwa index {arg.genome}')
	run(f'bwa mem {arg.genome} {arg.reads} -a > {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'gem3':
	if not os.path.exists(f'{arg.genome}.gem'): run(f'gem-indexer -i {arg.genome} -o {arg.genome}')
	run(f'gem-mapper -I {arg.genome}.gem -i {arg.reads} -t {arg.threads} > {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'gmap':
	if not os.path.exists(f'{arg.genome}-gmap'): run(f'gmap_build -d {arg.genome}-gmap -D . {arg.genome}')
	run(f'gunzip -c {arg.reads} | gmap -d {arg.genome}-gmap -D . -f samse -t {arg.threads} > {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'hst2':
	if not os.path.exists(f'{arg.genome}.1.ht2'): run(f'hisat2-build -f {arg.genome} {arg.genome}')
	run(f'hisat2 -x {arg.genome} -U {arg.reads} -f -p {arg.threads} > {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'magi': # note: renames the chromosomes as numbers
	if not os.path.exists(f'{arg.genome}.nsq'): run(f'makeblastdb -dbtype nucl -in {arg.genome}')
	run(f'magicblast -db {arg.genome} -query {arg.reads} -num_threads {arg.threads} > {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'min2':
	run(f'minimap2 -ax splice {arg.genome} {arg.reads} -t {arg.threads} > {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'novo':
	sys.exit('license required for novoalign') # should evaluate
elif arg.program == 'pblt': # note: reads need to be uncompressed (seekable)
	fasta = needfasta(arg)
	run(f'pblat {arg.genome} {fasta} {out} -threads={arg.threads} -out=sim4')
	sim4file_to_ftxfile(out, ftx)
elif arg.program == 'sege':
	if not os.path.exists(f'{arg.genome}.idx'): run(f'segemehl.x -x {arg.genome}.idx -d {arg.genome}')
	run(f'segemehl.x -i {arg.genome}.idx -d {arg.genome} -q {arg.reads} -t {arg.threads} --splits -o {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'star':
	if not os.path.exists(f'{arg.genome}-star'): run(f'STAR --runMode genomeGenerate --genomeDir {arg.genome}-star --genomeFastaFiles {arg.genome} --genomeSAindexNbases 8')
	run(f'STAR --genomeDir {arg.genome}-star --readFilesIn {arg.reads} --readFilesCommand "gunzip -c" --outFileNamePrefix {out} --runThreadN 1')
	os.rename(f'{out}Aligned.out.sam', f'{out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'subr':
	if not os.path.exists(f'{arg.genome}.00.b.tab'): run(f'subread-buildindex -o {arg.genome} {arg.genome}')
	run(f'subread-align -i {arg.genome} -r {arg.reads} -t 0 --SAMoutput --multiMapping -B 5 -T {arg.threads} -o {out}')
	samfile_to_ftxfile(out, ftx)
elif arg.program == 'top2':
	if not os.path.exists(f'{arg.genome}.1.bt2'): run(f'bowtie2-build {arg.genome} {arg.genome}')
	run(f'tophat2 -p {arg.threads} {arg.genome} {arg.reads}')
	run(f'samtools view -h tophat_out/accepted_hits.bam > {out}')
	samfile_to_ftxfile(out, ftx)
else:
	sys.exit(f'ERROR: unknown program: {arg.program}')

elapsed = time.time() - t0
print(f'BAKEOFF ELAPSED {arg.program}: {elapsed}', file=sys.stderr)

#####################
# Report Alignments #
#####################

refs = [name for name, seq in readfasta(arg.reads)]
aligned = {}
with open(ftx) as fp:
	for line in fp:
		ali, ref = line.rstrip().split('~')
		if ref not in aligned: aligned[ref] = ali
		else: aligned[ref] += '~' + ali # chaining extra alignments

with gzip.open(f'{arg.program}.ftx.gz', 'wt') as fp:
	for ref in refs:
		if ref in aligned: print(ref, aligned[ref], sep='\t', file=fp)
		else:              print(ref, 'None', sep='\t', file=fp)

############
# Clean up #
############

if not arg.debug and os.path.exists(out): os.unlink(f'{out}')
if not arg.debug and os.path.exists(ftx): os.unlink(f'{ftx}')