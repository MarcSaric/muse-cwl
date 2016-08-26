import argparse
import pipelineUtil
import uuid
import os
import sys
import postgres
import status_postgres
import setupLog
import logging
import tempfile
import time
import datetime
from elapsed_time import Time as Time

def update_postgres(exit, cwl_failure, vcf_upload_location, muse_location, logger):
    """ update the status of job on postgres """

    loc = 'UNKNOWN'
    status = 'UNKNOWN'

    if exit == 0:

        loc = vcf_upload_location

        if not(cwl_failure):

            status = 'COMPLETED'
            logger.info("uploaded all files to object store. The path is: %s" %muse_location)

        else:

            status = 'CWL_FAILED'
            logger.info("CWL failed but outputs were generated. The path is: %s" %muse_location)

    else:

        loc = 'Not Applicable'

        if not(cwl_failure):

            status = 'UPLOAD_FAILURE'
            logger.info("Upload of files failed")

        else:
            status = 'FAILED'
            logger.info("CWL and upload both failed")

    return(status, loc)

def is_nat(x):
    '''
    Checks that a value is a natural number.
    '''
    if int(x) > 0:
        return int(x)
    raise argparse.ArgumentTypeError('%s must be positive, non-zero' % x)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run MuSE variant calling CWL")
    required = parser.add_argument_group("Required input parameters")
    required.add_argument("--refdir", help="path to reference dir on object store")
    required.add_argument("--block", type=is_nat, default=50000000, help="parallel block size")
    required.add_argument('--thread_count', type=is_nat, default=8, help='thread count')
    required.add_argument('--host', default=None, help="hostname for db")

    required.add_argument("--normal", default=None, help="path to normal bam file")
    required.add_argument("--tumor", default=None, help="path to tumor bam file")
    required.add_argument("--normal_id", default=None, help="UUID for normal BAM")
    required.add_argument("--tumor_id", default=None, help="UUID for tumor BAM")
    required.add_argument("--case_id", default=None, help="UUID for case")
    required.add_argument("--index", default=None, help="Path to CWL BuildBamIndex tool code")
    required.add_argument("--cwl", default=None, help="Path to CWL code")

    optional = parser.add_argument_group("Optional input parameters")
    optional.add_argument("--s3dir", default="s3://ceph_kh11_baylor_muse_variant", help="path to output files")
    optional.add_argument("--basedir", default="/mnt/SCRATCH/", help="Base directory for computations")

    args = parser.parse_args()

    if not os.path.isdir(args.basedir):
        raise Exception("Could not find path to base directory: %s" %args.basedir)

    #create directory structure
    casedir = tempfile.mkdtemp(prefix="muse_%s_" %args.case_id, dir=args.basedir)
    workdir = tempfile.mkdtemp(prefix="workdir_", dir=casedir)
    inp = tempfile.mkdtemp(prefix="input_", dir=casedir)
    index = args.refdir

    #generate a random uuid
    vcf_uuid = uuid.uuid4()
    vcf_file = "%s.vcf" %(str(vcf_uuid))
    muse_location = os.path.join(args.s3dir, str(vcf_uuid))

    #setup logger
    log_file = os.path.join(workdir, "%s.muse.cwl.log" %str(vcf_uuid))
    logger = setupLog.setup_logging(logging.INFO, str(vcf_uuid), log_file)

    #logging inputs
    logger.info("normal_bam_path: %s" %(args.normal))
    logger.info("normal_bam_id: %s" %(args.normal_id))
    logger.info("tumor_bam_path: %s" %(args.tumor))
    logger.info("tumor_bam_id: %s" %(args.tumor_id))
    logger.info("case_id: %s" %(args.case_id))
    logger.info("vcf_id: %s" %(str(vcf_uuid)))

    #Get datetime
    datetime_now = str(datetime.datetime.now())
    #Get CWL start time
    cwl_start = time.time()

    #download
    logger.info("getting refs")
    reference_fasta_name = os.path.join(index,"GRCh38.d1.vd1.fa")
    reference_fasta_fai = os.path.join(index,"GRCh38.d1.vd1.fa.fai")
    dbsnp_known_snp_sites = os.path.join(index,"dbsnp_144.grch38.vcf.bgz")
    postgres_config = os.path.join(index,"postgres_config")

    #establish connection with database
    s = open(postgres_config, 'r').read()
    postgres_creds = eval(s)

    DATABASE = {
        'drivername': 'postgres',
        'host' : 'pgreadwrite.osdc.io',
        'port' : '5432',
        'username': postgres_creds['username'],
        'password' : postgres_creds['password'],
        'database' : 'prod_bioinfo'
    }

    engine = postgres.db_connect(DATABASE)

    logger.info("getting normal bam")
    normal_bam_input_url = str(args.normal)
    normal_bai_input_url = normal_bam_input_url[:-1]+'i'
    tumor_bam_input_url = str(args.tumor)
    tumor_bai_input_url = tumor_bam_input_url[:-1]+'i'
    if args.normal.startswith("s3://ceph_"):
        pipelineUtil.download_from_cleversafe(logger, normal_bam_input_url, str(inp), "ceph", "https://gdc-cephb-objstore.osdc.io/")
        pipelineUtil.download_from_cleversafe(logger, normal_bai_input_url, str(inp), "ceph", "https://gdc-cephb-objstore.osdc.io/")
        bam_norm = os.path.join(inp, os.path.basename(args.normal))
    else:
        pipelineUtil.download_from_cleversafe(logger, normal_bam_input_url, str(inp), "cleversafe", "https://gdc-accessors.osdc.io/")
        pipelineUtil.download_from_cleversafe(logger, normal_bai_input_url, str(inp), "cleversafe", "https://gdc-accessors.osdc.io/")
        bam_norm = os.path.join(inp, os.path.basename(args.normal))

    logger.info("getting tumor bam")
    if args.tumor.startswith("s3://ceph_"):
        pipelineUtil.download_from_cleversafe(logger, tumor_bam_input_url, str(inp), "ceph", "https://gdc-cephb-objstore.osdc.io/")
        pipelineUtil.download_from_cleversafe(logger, tumor_bai_input_url, str(inp), "ceph", "https://gdc-cephb-objstore.osdc.io/")
        bam_tumor = os.path.join(inp, os.path.basename(args.tumor))
    else:
        pipelineUtil.download_from_cleversafe(logger, tumor_bam_input_url, str(inp), "cleversafe", "https://gdc-accessors.osdc.io/")
        pipelineUtil.download_from_cleversafe(logger, tumor_bai_input_url, str(inp), "cleversafe", "https://gdc-accessors.osdc.io/")
        bam_tumor = os.path.join(inp, os.path.basename(args.tumor))

    os.chdir(workdir)
    #run cwl command
    cmd = ["/home/ubuntu/.virtualenvs/p2/bin/cwl-runner",
            "--debug",
            "--tmpdir-prefix", str(inp),
            "--tmp-outdir-prefix", str(workdir),
            str(args.cwl),
            "--reference_fasta_name", str(reference_fasta_name),
            "--reference_fasta_fai", str(reference_fasta_fai),
            "--normal_bam_path", str(bam_norm),
            "--tumor_bam_path", str(bam_tumor),
            "--normal_id", str(args.normal_id),
            "--tumor_id", str(args.tumor_id),
            "--dbsnp_known_snp_sites", str(dbsnp_known_snp_sites),
            "--Parallel_Block_Size", str(args.block),
            "--thread_count", str(args.thread_count),
            "--case_id", str(args.case_id),
            "--postgres_config", str(postgres_config),
            "--output_vcf", str(vcf_file),
            "--host", str(args.host)]

    cwl_exit = pipelineUtil.run_command(cmd, logger)

    cwl_failure = False
    if cwl_exit:
        cwl_failure = True

    #rename outputs
    orglog2 = os.path.join(workdir, "%s_muse_call.log" % args.case_id)
    if os.path.isfile(orglog2):
        os.rename(orglog2, os.path.join(workdir, "%s_muse_call.log" % str(vcf_uuid)))
    orglog3 = os.path.join(workdir, "%s_muse_sump_wxs.log" % args.case_id)
    if os.path.isfile(orglog3):
        os.rename(orglog3, os.path.join(workdir, "%s_muse_sump_wxs.log" % str(vcf_uuid)))

    #upload results to s3

    muse_location = os.path.join(args.s3dir, str(vcf_uuid))

    vcf_upload_location = os.path.join(muse_location, vcf_file)

    exit = pipelineUtil.upload_to_cleversafe(logger, muse_location, workdir, "ceph", "https://gdc-cephb-objstore.osdc.io/")

    cwl_end = time.time()
    cwl_elapsed = cwl_end - cwl_start

    status, loc = update_postgres(exit, cwl_failure, vcf_upload_location, muse_location, logger)

    met = Time(case_id = args.case_id,
               datetime_now = datetime_now,
               vcf_id = str(vcf_uuid),
               files = [args.normal_id, args.tumor_id],
               elapsed = cwl_elapsed,
               thread_count = str(args.thread_count),
               status = str(status))

    postgres.create_table(engine, met)
    postgres.add_metrics(engine, met)

    status_postgres.add_status(engine, args.case_id, str(vcf_uuid), [args.normal_id, args.tumor_id], status, loc)

    #remove work and input directories
    pipelineUtil.remove_dir(casedir)
