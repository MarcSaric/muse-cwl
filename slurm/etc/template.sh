#!/bin/bash
#SBATCH --nodes=1
#SBATCH --cpus-per-task=XX_THREAD_COUNT_XX
#SBATCH --ntasks=1
#SBATCH --mem=XX_MEM_XX
#SBATCH --workdir="/mnt/SCRATCH/"

function cleanup (){
    echo "cleanup tmp data";
    sudo rm -rf $basedir;
}

case_id="XX_CASEID_XX"
tumor_gdc_id="XX_TID_XX"
tumor_s3_url="XX_TS3URL_XX"
t_s3_profile="XX_TS3PROFILE_XX"
t_s3_endpoint="XX_TS3ENDPOINT_XX"
normal_gdc_id="XX_NID_XX"
normal_s3_url="XX_NS3URL_XX"
n_s3_profile="XX_NS3PROFILE_XX"
n_s3_endpoint="XX_NS3ENDPOINT_XX"

basedir=`sudo mktemp -d muse.XXXXXXXXXX -p /mnt/SCRATCH/`
refdir="XX_REFDIR_XX"
exp_strat="XX_EXP_STRAT_XX"
s3dir="XX_S3DIR_XX"
s3_profile="XX_S3PROFILE_XX"
s3_endpoint="XX_S3ENDPOINT_XX"

block="XX_BLOCKSIZE_XX"
thread_count="XX_THREAD_COUNT_XX"

repository="git@github.com:NCI-GDC/muse-cwl.git"
sudo chown ubuntu:ubuntu $basedir

cd $basedir

sudo git clone -b feat/workflow $repository muse-cwl
sudo chown ubuntu:ubuntu -R muse-cwl

trap cleanup EXIT

/home/ubuntu/.virtualenvs/p2/bin/python muse-cwl/slurm/gdc_muse_pipeline.py \
--case_id $case_id \
--tumor_gdc_id $tumor_gdc_id \
--tumor_s3_url $tumor_s3_url \
--t_s3_profile $t_s3_profile \
--t_s3_endpoint $t_s3_endpoint \
--normal_gdc_id $normal_gdc_id \
--normal_s3_url $normal_s3_url \
--n_s3_profile $n_s3_profile \
--n_s3_endpoint $n_s3_endpoint \
--basedir $basedir \
--refdir $refdir \
--cwl $basedir/muse-cwl/tools/muse_call.cwl \
--sort $basedir/muse-cwl/workflow/muse_sump_srt.cwl \
--exp_strat $exp_strat \
--s3dir $s3dir \
--s3_profile $s3_profile \
--s3_endpoint $s3_endpoint \
--block $block \
--thread_count $thread_count