#!/bin/bash
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --ntasks=1
#SBATCH --workdir=/mnt/SCRATCH/

normal="XX_NORMAL_XX"
tumor="XX_TUMOR_XX"
normal_id="XX_NORMAL_ID_XX"
tumor_id="XX_TUMOR_ID_XX"
case_id="XX_CASE_ID_XX"

basedir="/mnt/SCRATCH/"
ref="s3://bioinformatics_scratch/muse_ref/GRCh38.d1.vd1.fa"
refindex="s3://bioinformatics_scratch/muse_ref/GRCh38.d1.vd1.fa.fai"
refdict="s3://bioinformatics_scratch/muse_ref/GRCh38.d1.vd1.dict"
snp="s3://bioinformatics_scratch/muse_ref/dbsnp_144.grch38.vcf.bgz"
snpindex="s3://bioinformatics_scratch/muse_ref/dbsnp_144.grch38.vcf.bgz.tbi"

block="50000000"
thread_count="8"
username="username"
password="password"
repository="git@github.com:NCI-GDC/muse-cwl.git"
cwl="/home/ubuntu/muse-cwl/workflows/muse-wxs-workflow.cwl.yaml"
dir="/home/ubuntu/muse-cwl/"

if [ ! -d $dir ];then
    sudo git clone -b feat/slurm $repository $dir
    sudo chown ubuntu:ubuntu $dir
fi

/home/ubuntu/.virtualenvs/p2/bin/python /home/ubuntu/muse-cwl/slurm/run_cwl.py \
--ref $ref \
--refindex $refindex \
--refdict $refdict \
--snp $snp \
--snpindex $snpindex \
--block $block \
--thread_count $thread_count \
--normal $normal \
--tumor $tumor \
--normal_id $normal_id \
--tumor_id $tumor_id \
--case_id $case_id \
--username $username \
--password $password \
--basedir $basedir \
--cwl $cwl
