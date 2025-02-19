import sys
import os
import argparse
import logging
import scripts
from scripts import module
from datetime import datetime
from pathlib import Path
from glob import glob


def fetch_arguments(parser,root_dir,db_path_default):
    parser.set_defaults(func=main)
    parser.set_defaults(program="run")
    parser.add_argument('--input_metagenome','-i', dest='input_metagenome', required=True, default='none', help=r'(required) input metagenome assembly. It can be a metagenome or entire virome assembly. The extension of the input nucleotide sequence should be ".fasta"')
    parser.add_argument('--input_reads', '-r', dest = 'input_reads', required=True, default='none', help=r'(required) input metagenomic reads. The input paired reads should be  "forward_1.fastq or forward_R1.fastq" and "reverse_2.fastq or reverse_R2.fastq" connected by ",". Multiple paired reads can be provided at the same time for one metagenome assembly, connected by ",".  For example: -r /path/to/Lake_01_T1_1.fastq,/path/to/Lake_01_T1_2.fastq,/path/to/Lake_01_T2_1.fastq,/path/to/Lake_01_T2_2.fastq  Note that the extension of the input reads should be ".fastq" or ".fastq.gz"')
    parser.add_argument('--input_reads_type', '-rt', dest = 'input_reads_type', required=False, default='illumina', help=r'input metagenomic reads type. The default is illumina. If you are using long reads, you will need to assign: pacbio - PacBio CLR reads, pacbio_hifi - PacBio HiFi/CCS reads, pacbio_asm20 - PacBio HiFi/CCS reads asm20, nanopore - Oxford Nanopore reads')
    parser.add_argument('--reads_mapping_identity_cutoff', '-id', dest = 'reads_mapping_identity_cutoff', required=False, default=0.97, help=r'reads mapping identity cutoff. The default is 0.97. 0.97 is suitable for all illumina reads and also suitable for PacBio Sequel II or Nanopore PromethION Q20+ reads. For other PacBio or Nanopore reads with high error rate, the id cutoff is suggested to be 1 - error rate')
    parser.add_argument('--out_dir','-o', dest='out_dir', required=False, default='./ViWrap_outdir', help=r'(required) output directory to deposit all results (default = ./ViWrap_outdir) output folder to deposit all results. ViWrap will exit if the folder already exists')
    parser.add_argument('--db_dir','-d', dest='db_dir', required=False, default=db_path_default, help=f'(required) database directory; default = {db_path_default}')
    parser.add_argument('--identify_method', dest='identify_method', required=False, default='vb-vs',help=r'(required) the virus identifying method to choose: vb - VIBRANT; vs - VirSorter2 and CheckV; dvf - DeepVirFinder; vb-vs - Use VIBRANT and VirSorter2 to get the overlapped viruses (default); vb-vs-dvf - Use all these three methods and get the overlapped viruses')
    parser.add_argument('--conda_env_dir', dest='conda_env_dir', required=True, default='none', help=r'(required) the directory where you put your conda environment files. It is the parent directory that contains all the conda environment folders')
    parser.add_argument('--threads','-t', dest='threads', required=False, default=10, help=r'number of threads (default = 10)')
    parser.add_argument('--virome','-v', dest='virome', action='store_true', required=False, default=False, help=r"edit VIBRANT's sensitivity if the input dataset is a virome. It is suggested to use it if you know that the input assembly is virome or metagenome")
    parser.add_argument('--input_length_limit', dest='input_length_limit', required=False, default=2000, help=r'length in basepairs to limit input sequences (default=2000, can increase but not decrease); 2000 at least suggested for VIBRANT (vb)-based pipeline, 5000 at least suggested for VirSorter2 (vs)-based pipeline')
    parser.add_argument('--custom_MAGs_dir', dest='custom_MAGs_dir', required=False, default='none', help=r'custom MAGs dir that contains only *.fasta files for MAGs reconstructed from the same metagenome, this will be used in iPHoP for host prediction; note that it should be the absolute address path')	
    parser.add_argument('--iPHoP_db_custom_pre', dest='iPHoP_db_custom_pre', required=False, default='none', help=r'custom iPHoP db that has been made from the previous run, this will be used in iPHoP for host prediction by custom db; note that it should be the absolute address path')
    parser.add_argument('--root_dir', dest='root_dir', required=False, default=root_dir,help=argparse.SUPPRESS)
    

def set_defaults(args):
    ## Store databases
    args['CheckV_db'] = os.path.join(args['db_dir'],'CheckV_db')
    args['DRAM_db'] = os.path.join(args['db_dir'],'DRAM_db')
    args['GTDB_db'] = os.path.join(args['db_dir'],'GTDB_db')
    args['iPHoP_db'] = os.path.join(args['db_dir'],'iPHoP_db/iPHoP_db')
    args['iPHoP_db_custom'] = os.path.join(args['db_dir'],'iPHoP_db_custom') 
    args['Kofam_db'] = os.path.join(args['db_dir'],'Kofam_db')
    args['Tax_classification_db'] = os.path.join(args['db_dir'],'Tax_classification_db')
    args['VIBRANT_db'] = os.path.join(args['db_dir'],'VIBRANT_db')
    args['VirSorter2_db'] = os.path.join(args['db_dir'],'VirSorter2_db')
    args['DVF_db'] = os.path.join(args['db_dir'],'DVF_db')
    
    ## Store outdirs 
    args['vibrant_outdir'] = os.path.join(args['out_dir'],f"00_VIBRANT_{Path(args['input_metagenome']).stem}")
    args['virsorter_outdir'] = os.path.join(args['out_dir'],f"00_VirSorter_{Path(args['input_metagenome']).stem}")
    args['dvf_outdir'] = os.path.join(args['out_dir'],f"00_DeepVirFinder_{Path(args['input_metagenome']).stem}")
    args['vb_vs_dvf_outdir'] = os.path.join(args['out_dir'],f"00_VIBRANT_VirSorter_DeepVirFinder_{Path(args['input_metagenome']).stem}")
    args['vb_vs_outdir'] = os.path.join(args['out_dir'],f"00_VIBRANT_VirSorter_{Path(args['input_metagenome']).stem}")
    args['mapping_outdir'] = os.path.join(args['out_dir'],'01_Mapping_result_outdir')
    args['vrhyme_outdir'] = os.path.join(args['out_dir'],'02_vRhyme_outdir')
    args['vcontact2_outdir'] = os.path.join(args['out_dir'],'03_vConTACT2_outdir')
    args['nlinked_viral_gn_dir'] = os.path.join(args['out_dir'],'04_Nlinked_viral_gn_dir')
    args['checkv_outdir'] = os.path.join(args['out_dir'],'05_CheckV_outdir')
    args['drep_outdir'] = os.path.join(args['out_dir'],'06_dRep_outdir')
    args['iphop_outdir'] = os.path.join(args['out_dir'],'07_iPHoP_outdir')
    args['iphop_custom_outdir'] = os.path.join(args['out_dir'],'07_iPHoP_outdir/iPHoP_outdir_custom_MAGs')
    args['viwrap_summary_outdir'] = os.path.join(args['out_dir'],'08_ViWrap_summary_outdir')
    args['viwrap_visualization_outdir'] = os.path.join(args['out_dir'],'09_Virus_statistics_visualization')
    
def main(args):
    # Welcome and logger
    print("### Welcome to ViWrap ###\n") 

	## Set up the logger
    os.mkdir(args['out_dir'])
    log_file = os.path.join(args['out_dir'],'ViWrap_run.log')
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )    
    logger = logging.getLogger(__name__) 

    ## Store the input arguments
    issued_command = scripts.module.get_run_input_arguments(args)
    logger.info(f"The issued command is:\n{issued_command}\n")
    
    ## Set the default args:
    set_defaults(args)
    
    # Step 1 Pre-check inputs
    start_time = datetime.now().replace(microsecond=0)
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Pre-check inputings. In processing...")
    
    if not os.path.exists(args['input_metagenome']):
        sys.exit(f"Could not find input metagenome {args['input_metagenome']}")        
    if not os.path.exists(args['db_dir']):
        sys.exit(f"Could not find directory {args['db_dir']}. Maybe the database directory was not specified with the --db_dir and is not the default \".ViWrap_db/\" directory?")

    if args['input_reads_type'] != 'illumina' and args['input_reads_type'] != 'pacbio' and args['input_reads_type'] != 'pacbio_hifi' and args['input_reads_type'] != 'pacbio_asm20' and args['input_reads_type'] != 'nanopore':
        sys.exit(f"The input reads type should be one of these: illumina, pacbio, pacbio_hifi, pacbio_asm20, and nanopore")  
        
    metaG_reads_list = args['input_reads'].split(',')
    for each_read in metaG_reads_list:
        if not each_read.endswith('.fastq') and not each_read.endswith('.fastq.gz'):
            sys.exit(f"Please make sure that all your input reads are ended with .fastq or fastq.gz")  
    
    sample2read_info = scripts.module.get_read_info(args['input_reads'], args['input_reads_type'])  
    
    if args['custom_MAGs_dir'] != 'none' and not os.path.exists(args['custom_MAGs_dir']):
        sys.exit(f"Could not find custom MAGs directory {args['custom_MAGs_dir']}. Maybe the directory is not correct")
    elif args['custom_MAGs_dir'] != 'none' and os.path.exists(args['custom_MAGs_dir']):   
        for file in glob(f"os.path.join(args['custom_MAGs_dir'],'*.fasta')"):
            if '.fasta' not in file:
                sys.exit(f"Make sure all MAGs in custom MAGs directory {args['custom_MAGs_dir']} end with \'.fasta\', and no additional files within the directory")
                
    if args['custom_MAGs_dir'] != 'none' and not os.path.isabs(args['custom_MAGs_dir']):
        sys.exit(f"Please make sure that the path to custom MAGs directory {args['custom_MAGs_dir']} is a full absolute path")
                
    if not os.path.exists(args['conda_env_dir']):
        sys.exit(f"Could not find conda env dirs within {args['conda_env_dir']}") 
    
    if os.path.exists(args['iPHoP_db_custom']):
        sys.exit(f"Please make sure that {args['iPHoP_db_custom']} is not present before ViWrap run. If present, please remove the folder") 

    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Looks like the input metagenome and reads, database, and custom MAGs dir (if option used) are now set up well, start up to run ViWrap pipeline")
         

    # Step 2 Run VIBRANT or VirSorter2 or DVF
    if args['identify_method'] == 'vb':
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT to identify and annotate virus from input metagenome. In processing...")
    
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {args['input_metagenome']} {args['out_dir']} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
        default_vibrant_outdir = os.path.join(args['out_dir'],f"VIBRANT_{Path(args['input_metagenome']).stem}")
        os.system(f"mv {default_vibrant_outdir} {args['vibrant_outdir']}")
        scripts.module.parse_vibrant_lytic_and_lysogenic_info(args['vibrant_outdir'], Path(args['input_metagenome']).stem)
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT to identify and annotate viruses from input metagenome. Finished")      

    elif args['identify_method'] == 'vs':
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VirSorter2 to identify viruses from input metagenome. Also plus CheckV to QC and trim, and KEGG, Pfam, and VOG HMMs to annotate viruses. In processing...")    
    
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vs2')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_1st.py')} {args['input_metagenome']} {args['virsorter_outdir']} {args['threads']} {args['input_length_limit']} ") # >/dev/null 2>&1
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VirSorter2 the 1st time to identify viruses from input metagenome. Finished")    

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_CheckV_1st.py')} {args['virsorter_outdir']} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run CheckV the 1st time to QC and trim viruses identified from VirSorter2 1st run. Finished")   
        
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vs2')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_2nd.py')} {args['virsorter_outdir']} {args['threads']} {args['input_length_limit']} >/dev/null 2>&1")
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VirSorter2 the 2nd time for CheckV-trimmed sequences. Finished")    

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_CheckV_2nd.py')} {args['virsorter_outdir']} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run CheckV the 2nd time to get viral and host gene counts. Finished")

        keep1_list_file = os.path.join(args['virsorter_outdir'], 'keep1_list.txt')
        keep2_list_file = os.path.join(args['virsorter_outdir'], 'keep2_list.txt')
        discard_list_file = os.path.join(args['virsorter_outdir'], 'discard_list.txt')
        manual_check_list_file = os.path.join(args['virsorter_outdir'], 'manual_check_list.txt')
        scripts.module.screen_virsorter2_result(args['virsorter_outdir'], keep1_list_file, keep2_list_file, discard_list_file, manual_check_list_file)
        
        keep2_fasta = os.path.join(args['virsorter_outdir'], 'keep2.fasta')
        manual_check_fasta = os.path.join(args['virsorter_outdir'], 'manual_check.fasta')
        scripts.module.get_keep2_mc_seq(args['virsorter_outdir'], keep2_list_file, manual_check_list_file, keep2_fasta, manual_check_fasta)
        
        if os.path.exists(keep2_fasta) and os.path.getsize(keep2_fasta) != 0:
            os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {keep2_fasta} {args['virsorter_outdir']} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
            keep2_vb_result = os.path.join(args['virsorter_outdir'], 'VIBRANT_keep2/VIBRANT_phages_keep2/keep2.phages_combined.fna') 
            keep2_list_vb_passed_file = os.path.join(args['virsorter_outdir'], 'keep2_list_vb_passed.txt')
            scripts.module.get_keep2_vb_passed_list(args['virsorter_outdir'], keep2_vb_result, keep2_list_vb_passed_file)
            os.system(f"rm -r {os.path.join(args['virsorter_outdir'], 'VIBRANT_keep2')}")
        if os.path.exists(manual_check_fasta) and os.path.getsize(manual_check_fasta) != 0:
            os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {manual_check_fasta} {args['virsorter_outdir']} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
            manual_check_vb_result = os.path.join(args['virsorter_outdir'], 'VIBRANT_manual_check/VIBRANT_phages_manual_check/manual_check.phages_combined.fna') 
            manual_check_list_vb_passed_file = os.path.join(args['virsorter_outdir'], 'manual_check_list_vb_passed.txt')
            scripts.module.get_manual_check_vb_passed_list(args['virsorter_outdir'], manual_check_vb_result, manual_check_list_vb_passed_file)
            os.system(f"rm -r {os.path.join(args['virsorter_outdir'], 'VIBRANT_manual_check')}")            

        keep2_list_vb_passed_file = os.path.join(args['virsorter_outdir'], 'keep2_list_vb_passed.txt')
        manual_check_list_vb_passed_file = os.path.join(args['virsorter_outdir'], 'manual_check_list_vb_passed.txt')
        final_vs2_virus_fasta_file = os.path.join(args['virsorter_outdir'], 'final_vs2_virus.fasta')
        scripts.module.get_final_vs2_virus(args['virsorter_outdir'], keep1_list_file, keep2_list_vb_passed_file, manual_check_list_vb_passed_file, final_vs2_virus_fasta_file)
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT to check \"keep2\" and \"manual_check\" groups and get the final VirSorter2 virus sequences. Finished")  

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_annotate_by_VIBRANT_db.py')} {args['VIBRANT_db']} {args['identify_method']} {args['virsorter_outdir']} {args['dvf_outdir']} {args['out_dir']} {args['threads']}")

        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Use KEGG, Pfam, and VOG HMMs to annotate viruses. Finished") 
        
    elif args['identify_method'] == 'dvf':
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-DVF')} python {os.path.join(args['root_dir'],'scripts/run_DVF.py')} {args['input_metagenome']} {args['dvf_outdir']} {args['input_length_limit']} {args['DVF_db']} >/dev/null 2>&1")
        final_dvf_virus_fasta_file = os.path.join(args['dvf_outdir'], 'final_dvf_virus.fasta')
        scripts.module.get_dvf_result_seq(args, args['dvf_outdir'], final_dvf_virus_fasta_file)
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run DeepVirFinder to identify viruses from input metagenome. Finished")   

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_annotate_by_VIBRANT_db.py')} {args['VIBRANT_db']} {args['identify_method']} {args['virsorter_outdir']} {args['dvf_outdir']} {args['out_dir']} {args['threads']}") 
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Use KEGG, Pfam, and VOG HMMs to annotate viruses. Finished") 
        
    elif args['identify_method'] == 'vb-vs-dvf':
        ## Set output folders
        inner_vb_outdir = os.path.join(args['vb_vs_dvf_outdir'],f"VIBRANT_{Path(args['input_metagenome']).stem}")
        inner_vs_outdir = os.path.join(args['vb_vs_dvf_outdir'],f"VirSorter_{Path(args['input_metagenome']).stem}")
        inner_dvf_outdir = os.path.join(args['vb_vs_dvf_outdir'],f"DeepVirFinder_{Path(args['input_metagenome']).stem}")
        
        ## Firstly, run VIBRANT 
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run VIBRANT to identify and annotate virus from input metagenome. In processing...")
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {args['input_metagenome']} {args['vb_vs_dvf_outdir']} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
        scripts.module.parse_vibrant_lytic_and_lysogenic_info(inner_vb_outdir, Path(args['input_metagenome']).stem)
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run VIBRANT to identify and annotate viruses from input metagenome. Finished") 
        
        ## Secondly, run VirSorter2
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run VirSorter2 to identify viruses from input metagenome. Also plus CheckV to QC and trim, and KEGG, Pfam, and VOG HMMs to annotate viruses. In processing...")    
    
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vs2')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_1st.py')} {args['input_metagenome']} {inner_vs_outdir} {args['threads']} {args['input_length_limit']} >/dev/null 2>&1")
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run VirSorter2 the 1st time to identify viruses from input metagenome. Finished")    

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_CheckV_1st.py')} {inner_vs_outdir} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run CheckV the 1st time to QC and trim viruses identified from VirSorter2 1st run. Finished")   
        
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vs2')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_2nd.py')} {inner_vs_outdir} {args['threads']} {args['input_length_limit']} >/dev/null 2>&1")
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run VirSorter2 the 2nd time for CheckV-trimmed sequences. Finished")    

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_CheckV_2nd.py')} {inner_vs_outdir} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run CheckV the 2nd time to get viral and host gene counts. Finished")

        keep1_list_file = os.path.join(inner_vs_outdir, 'keep1_list.txt')
        keep2_list_file = os.path.join(inner_vs_outdir, 'keep2_list.txt')
        discard_list_file = os.path.join(inner_vs_outdir, 'discard_list.txt')
        manual_check_list_file = os.path.join(inner_vs_outdir, 'manual_check_list.txt')
        scripts.module.screen_virsorter2_result(inner_vs_outdir, keep1_list_file, keep2_list_file, discard_list_file, manual_check_list_file)
        
        keep2_fasta = os.path.join(inner_vs_outdir, 'keep2.fasta')
        manual_check_fasta = os.path.join(inner_vs_outdir, 'manual_check.fasta')
        scripts.module.get_keep2_mc_seq(inner_vs_outdir, keep2_list_file, manual_check_list_file, keep2_fasta, manual_check_fasta)
        
        if os.path.exists(keep2_fasta) and os.path.getsize(keep2_fasta) != 0:
            os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {keep2_fasta} {inner_vs_outdir} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
            keep2_vb_result = os.path.join(inner_vs_outdir, 'VIBRANT_keep2/VIBRANT_phages_keep2/keep2.phages_combined.fna') 
            keep2_list_vb_passed_file = os.path.join(inner_vs_outdir, 'keep2_list_vb_passed.txt')
            scripts.module.get_keep2_vb_passed_list(inner_vs_outdir, keep2_vb_result, keep2_list_vb_passed_file)
            os.system(f"rm -r {os.path.join(inner_vs_outdir, 'VIBRANT_keep2')}")
        if os.path.exists(manual_check_fasta) and os.path.getsize(manual_check_fasta) != 0:
            os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {manual_check_fasta} {inner_vs_outdir} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
            manual_check_vb_result = os.path.join(inner_vs_outdir, 'VIBRANT_manual_check/VIBRANT_phages_manual_check/manual_check.phages_combined.fna') 
            manual_check_list_vb_passed_file = os.path.join(inner_vs_outdir, 'manual_check_list_vb_passed.txt')
            scripts.module.get_manual_check_vb_passed_list(inner_vs_outdir, manual_check_vb_result, manual_check_list_vb_passed_file)
            os.system(f"rm -r {os.path.join(inner_vs_outdir, 'VIBRANT_manual_check')}")            

        keep2_list_vb_passed_file = os.path.join(inner_vs_outdir, 'keep2_list_vb_passed.txt')
        manual_check_list_vb_passed_file = os.path.join(inner_vs_outdir, 'manual_check_list_vb_passed.txt')
        final_vs2_virus_fasta_file = os.path.join(inner_vs_outdir, 'final_vs2_virus.fasta')
        scripts.module.get_final_vs2_virus(inner_vs_outdir, keep1_list_file, keep2_list_vb_passed_file, manual_check_list_vb_passed_file, final_vs2_virus_fasta_file)
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run VIBRANT to check \"keep2\" and \"manual_check\" groups and get the final VirSorter2 virus sequences. Finished")  
       
        ## Thirdly, run DVF
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-DVF')} python {os.path.join(args['root_dir'],'scripts/run_DVF.py')} {args['input_metagenome']} {inner_dvf_outdir} {args['input_length_limit']} {args['DVF_db']} >/dev/null 2>&1")
        final_dvf_virus_fasta_file = os.path.join(inner_dvf_outdir, 'final_dvf_virus.fasta')
        scripts.module.get_dvf_result_seq(args, inner_dvf_outdir, final_dvf_virus_fasta_file)
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2-DVF method. Run DeepVirFinder to identify viruses from input metagenome. Finished")   
        
        ## Fourly, get the overlapped result
        overlap_outdir = os.path.join(args['vb_vs_dvf_outdir'],f"Overlap_{Path(args['input_metagenome']).stem}")
        final_vb_virus_fasta_file = os.path.join(inner_vb_outdir, f"VIBRANT_phages_{Path(args['input_metagenome']).stem}", f"{Path(args['input_metagenome']).stem}.phages_combined.fna")
        final_vs2_virus_fasta_file = os.path.join(inner_vs_outdir, 'final_vs2_virus.fasta')
        final_dvf_virus_fasta_file = os.path.join(inner_dvf_outdir, 'final_dvf_virus.fasta')
        final_vb_virus_annotation_file = os.path.join(inner_vb_outdir, f"VIBRANT_results_{Path(args['input_metagenome']).stem}", f"VIBRANT_annotations_{Path(args['input_metagenome']).stem}.tsv")
        scripts.module.get_overlapped_viral_scaffolds(final_vb_virus_fasta_file, final_vs2_virus_fasta_file, final_dvf_virus_fasta_file, final_vb_virus_annotation_file, overlap_outdir)
        
    elif args['identify_method'] == 'vb-vs':
        ## Set output folders
        inner_vb_outdir = os.path.join(args['vb_vs_outdir'],f"VIBRANT_{Path(args['input_metagenome']).stem}")
        inner_vs_outdir = os.path.join(args['vb_vs_outdir'],f"VirSorter_{Path(args['input_metagenome']).stem}")
        
        ## Firstly, run VIBRANT 
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run VIBRANT to identify and annotate virus from input metagenome. In processing...")
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {args['input_metagenome']} {args['vb_vs_outdir']} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
        scripts.module.parse_vibrant_lytic_and_lysogenic_info(inner_vb_outdir, Path(args['input_metagenome']).stem)
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run VIBRANT to identify and annotate viruses from input metagenome. Finished") 
        
        ## Secondly, run VirSorter2
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run VirSorter2 to identify viruses from input metagenome. Also plus CheckV to QC and trim, and KEGG, Pfam, and VOG HMMs to annotate viruses. In processing...")    
    
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vs2')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_1st.py')} {args['input_metagenome']} {inner_vs_outdir} {args['threads']} {args['input_length_limit']} >/dev/null 2>&1")
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run VirSorter2 the 1st time to identify viruses from input metagenome. Finished")    

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_CheckV_1st.py')} {inner_vs_outdir} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run CheckV the 1st time to QC and trim viruses identified from VirSorter2 1st run. Finished")   
        
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vs2')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_2nd.py')} {inner_vs_outdir} {args['threads']} {args['input_length_limit']} >/dev/null 2>&1")
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run VirSorter2 the 2nd time for CheckV-trimmed sequences. Finished")    

        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_VirSorter2_CheckV_2nd.py')} {inner_vs_outdir} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run CheckV the 2nd time to get viral and host gene counts. Finished")

        keep1_list_file = os.path.join(inner_vs_outdir, 'keep1_list.txt')
        keep2_list_file = os.path.join(inner_vs_outdir, 'keep2_list.txt')
        discard_list_file = os.path.join(inner_vs_outdir, 'discard_list.txt')
        manual_check_list_file = os.path.join(inner_vs_outdir, 'manual_check_list.txt')
        scripts.module.screen_virsorter2_result(inner_vs_outdir, keep1_list_file, keep2_list_file, discard_list_file, manual_check_list_file)
        
        keep2_fasta = os.path.join(inner_vs_outdir, 'keep2.fasta')
        manual_check_fasta = os.path.join(inner_vs_outdir, 'manual_check.fasta')
        scripts.module.get_keep2_mc_seq(inner_vs_outdir, keep2_list_file, manual_check_list_file, keep2_fasta, manual_check_fasta)
        
        if os.path.exists(keep2_fasta) and os.path.getsize(keep2_fasta) != 0:
            os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {keep2_fasta} {inner_vs_outdir} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
            keep2_vb_result = os.path.join(inner_vs_outdir, 'VIBRANT_keep2/VIBRANT_phages_keep2/keep2.phages_combined.fna') 
            keep2_list_vb_passed_file = os.path.join(inner_vs_outdir, 'keep2_list_vb_passed.txt')
            scripts.module.get_keep2_vb_passed_list(inner_vs_outdir, keep2_vb_result, keep2_list_vb_passed_file)
            os.system(f"rm -r {os.path.join(inner_vs_outdir, 'VIBRANT_keep2')}")
        if os.path.exists(manual_check_fasta) and os.path.getsize(manual_check_fasta) != 0:
            os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-VIBRANT')} python {os.path.join(args['root_dir'],'scripts/run_VIBRANT.py')} {manual_check_fasta} {inner_vs_outdir} {args['threads']} {args['virome']} {args['input_length_limit']} {args['db_dir']} >/dev/null 2>&1")
            manual_check_vb_result = os.path.join(inner_vs_outdir, 'VIBRANT_manual_check/VIBRANT_phages_manual_check/manual_check.phages_combined.fna') 
            manual_check_list_vb_passed_file = os.path.join(inner_vs_outdir, 'manual_check_list_vb_passed.txt')
            scripts.module.get_manual_check_vb_passed_list(inner_vs_outdir, manual_check_vb_result, manual_check_list_vb_passed_file)
            os.system(f"rm -r {os.path.join(inner_vs_outdir, 'VIBRANT_manual_check')}")            

        keep2_list_vb_passed_file = os.path.join(inner_vs_outdir, 'keep2_list_vb_passed.txt')
        manual_check_list_vb_passed_file = os.path.join(inner_vs_outdir, 'manual_check_list_vb_passed.txt')
        final_vs2_virus_fasta_file = os.path.join(inner_vs_outdir, 'final_vs2_virus.fasta')
        scripts.module.get_final_vs2_virus(inner_vs_outdir, keep1_list_file, keep2_list_vb_passed_file, manual_check_list_vb_passed_file, final_vs2_virus_fasta_file)
        
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Run VIBRANT-VirSorter2 method. Run VIBRANT to check \"keep2\" and \"manual_check\" groups and get the final VirSorter2 virus sequences. Finished")  
                  
        ## Thirdly, get the overlapped result
        overlap_outdir = os.path.join(args['vb_vs_outdir'],f"Overlap_{Path(args['input_metagenome']).stem}")
        final_vb_virus_fasta_file = os.path.join(inner_vb_outdir, f"VIBRANT_phages_{Path(args['input_metagenome']).stem}", f"{Path(args['input_metagenome']).stem}.phages_combined.fna")
        final_vs2_virus_fasta_file = os.path.join(inner_vs_outdir, 'final_vs2_virus.fasta')
        final_vb_virus_annotation_file = os.path.join(inner_vb_outdir, f"VIBRANT_results_{Path(args['input_metagenome']).stem}", f"VIBRANT_annotations_{Path(args['input_metagenome']).stem}.tsv")
        scripts.module.get_overlapped_viral_scaffolds(final_vb_virus_fasta_file, final_vs2_virus_fasta_file, '', final_vb_virus_annotation_file, overlap_outdir)
    
    else:
        sys.exit(f"Please make sure your input for --identify_method option is one of these: \"vb-vs\", \"vb-vs-dvf\", \"vb\", \"vs\", and \"dvf\"; you can also omit this in the command line, the default is \"vb\"")


    # Step 3 Metagenomic mapping
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Map reads to metagenome. In processing...")
    
    viral_scaffold = ''
    if args['identify_method'] == 'vb':
        viral_scaffold = os.path.join(args['vibrant_outdir'],f"VIBRANT_phages_{Path(args['input_metagenome']).stem}",f"{Path(args['input_metagenome']).stem}.phages_combined.fna")
    elif args['identify_method'] == 'vs':
        viral_scaffold = os.path.join(args['virsorter_outdir'], 'final_vs2_virus.fasta')
    elif args['identify_method'] == 'dvf':
        viral_scaffold = os.path.join(args['dvf_outdir'], 'final_dvf_virus.fasta')  
    elif args['identify_method'] == 'vb-vs-dvf':
        viral_scaffold = os.path.join(args['vb_vs_dvf_outdir'], f"Overlap_{Path(args['input_metagenome']).stem}", 'final_overlapped_virus.fasta')   
    elif args['identify_method'] == 'vb-vs':        
        viral_scaffold = os.path.join(args['vb_vs_outdir'], f"Overlap_{Path(args['input_metagenome']).stem}", 'final_overlapped_virus.fasta')   
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-Mapping')} python {os.path.join(args['root_dir'],'scripts/mapping_metaG_reads.py')} {viral_scaffold} {args['input_metagenome']} {args['input_reads']} {args['mapping_outdir']} {args['input_reads_type']} {args['reads_mapping_identity_cutoff']} {args['threads']} >/dev/null 2>&1")

    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Map reads to metagenome. Finished")
   

    # Step 4 Run vRhyme
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run vRhyme to bin viral scaffolds. In processing...")        
    
    ## Step 4.1 Run vRhyme to get the original vRhyme_best_bins    
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vRhyme')} python {os.path.join(args['root_dir'],'scripts/run_vRhyme.py')} {viral_scaffold} {args['vrhyme_outdir']} {args['mapping_outdir']} {args['threads']} >/dev/null 2>&1")
    vRhyme_best_bin_dir = os.path.join(args['vrhyme_outdir'], 'vRhyme_best_bins_fasta')
       
    ## Step 4.2 Get the lytic and lysogenic information for vRhyme_best_bins 
    scf2lytic_or_lyso_summary = ''
    if args['identify_method'] == 'vb':
        scf2lytic_or_lyso_summary = os.path.join(args['vibrant_outdir'], 'scf2lytic_or_lyso.summary.txt')
    elif args['identify_method'] == 'vb-vs-dvf':
        scf2lytic_or_lyso_summary = os.path.join(args['vb_vs_dvf_outdir'],f"VIBRANT_{Path(args['input_metagenome']).stem}", 'scf2lytic_or_lyso.summary.txt')
    elif args['identify_method'] == 'vb-vs':        
        scf2lytic_or_lyso_summary = os.path.join(args['vb_vs_outdir'],f"VIBRANT_{Path(args['input_metagenome']).stem}", 'scf2lytic_or_lyso.summary.txt')
    scripts.module.get_vRhyme_best_bin_lytic_and_lysogenic_info(vRhyme_best_bin_dir, args['vrhyme_outdir'], scf2lytic_or_lyso_summary)
    vRhyme_best_bin_lytic_and_lysogenic_info = os.path.join(args['vrhyme_outdir'], 'vRhyme_best_bin_lytic_and_lysogenic_info.txt')
        
    ## Step 4.3 Get the scaffold complete information for vRhyme_best_bins
    vRhyme_best_bin_CheckV_result = os.path.join(args['vrhyme_outdir'], 'vRhyme_best_bins_fasta_CheckV_result')
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_CheckV.py')} {vRhyme_best_bin_dir} {vRhyme_best_bin_CheckV_result} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
    CheckV_quality_summary = os.path.join(vRhyme_best_bin_CheckV_result, 'CheckV_quality_summary.txt')
    scripts.module.parse_checkv_result(vRhyme_best_bin_CheckV_result, CheckV_quality_summary)   
    vRhyme_best_bin_scaffold_complete_info = os.path.join(args['vrhyme_outdir'], 'vRhyme_best_bin_scaffold_complete_info.txt')  
    scripts.module.get_vRhyme_best_bin_scaffold_complete_info(CheckV_quality_summary, vRhyme_best_bin_scaffold_complete_info)
    os.system(f"rm -rf {vRhyme_best_bin_CheckV_result}")
    
    ## Step 4.4 Get modified vRhyme_best_bins acccording to both lytic and lysogenic and scaffold complete information
    vRhyme_best_bin_dir_modified = os.path.join(args['vrhyme_outdir'], 'vRhyme_best_bins_fasta_modified')
    scripts.module.make_vRhyme_best_bins_fasta_modified(vRhyme_best_bin_dir, vRhyme_best_bin_dir_modified, vRhyme_best_bin_lytic_and_lysogenic_info, vRhyme_best_bin_scaffold_complete_info)    

    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run vRhyme to bin viral scaffolds. Finished") 
    
    
    # Step 5 Run vContact2
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run vContact2 to cluster viral genomes. In processing...")    
    ## Step 5.1 Make unbinned viral gn folder
    vRhyme_unbinned_viral_gn_dir = os.path.join(args['vrhyme_outdir'], 'vRhyme_unbinned_viral_gn_fasta')
    scripts.module.make_unbinned_viral_gn(viral_scaffold, vRhyme_best_bin_dir_modified, vRhyme_unbinned_viral_gn_dir)

    ## Step 5.2 Prepare pro2viral_gn map file
    pro2viral_gn_map = os.path.join(args['vrhyme_outdir'], 'pro2viral_gn_map.csv')
    scripts.module.get_pro2viral_gn_map(vRhyme_best_bin_dir_modified, vRhyme_unbinned_viral_gn_dir, pro2viral_gn_map)

    ## Step 5.3 Make all vRhyme viral gn combined faa file
    all_vRhyme_faa = os.path.join(args['vrhyme_outdir'], 'all_vRhyme_faa.faa')
    scripts.module.combine_all_vRhyme_faa(vRhyme_best_bin_dir_modified, vRhyme_unbinned_viral_gn_dir, all_vRhyme_faa)

    ## Step 5.4 Run vContact2
    cluster_one_jar = os.path.join(args['conda_env_dir'], 'ViWrap-vContact2/bin/cluster_one-1.0.jar')
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-vContact2')} python {os.path.join(args['root_dir'],'scripts/run_vContact2.py')} {all_vRhyme_faa} {pro2viral_gn_map} {args['Tax_classification_db']} {cluster_one_jar} {args['vcontact2_outdir']} {args['threads']} >/dev/null 2>&1")


    ## Step 5.5 Write down genus cluster info
    genome_by_genome_file = os.path.join(args['vcontact2_outdir'], 'genome_by_genome_overview.csv')
    genus_cluster_info = os.path.join(args['out_dir'], 'Genus_cluster_info.txt')
    ref_pro2viral_gn_map = os.path.join(args['Tax_classification_db'], 'IMGVR_high-quality_phage_vOTU_representatives_pro2viral_gn_map.csv')
    scripts.module.get_genus_cluster_info(genome_by_genome_file, genus_cluster_info, ref_pro2viral_gn_map) 
 
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run vContact2 to cluster viral genomes. Finished")   
    

    # Step 6 Run CheckV
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run CheckV to evaluate virus genome quality. In processing...")       
    ## Step 6.1 Link multiple scaffolds within a bin
    os.mkdir(args['nlinked_viral_gn_dir'])
    scripts.module.Nlinker(vRhyme_best_bin_dir_modified, args['nlinked_viral_gn_dir'], 'fasta', 1000)  
    scripts.module.Nlinker(vRhyme_unbinned_viral_gn_dir, args['nlinked_viral_gn_dir'], 'fasta', 1000) 

    ## Step 6.2 Run CheckV in parallel and parse the result
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-CheckV')} python {os.path.join(args['root_dir'],'scripts/run_CheckV.py')} {args['nlinked_viral_gn_dir']} {args['checkv_outdir']} {args['threads']} {args['CheckV_db']} >/dev/null 2>&1")
    CheckV_quality_summary = os.path.join(args['checkv_outdir'], 'CheckV_quality_summary.txt')
    scripts.module.parse_checkv_result(args['checkv_outdir'], CheckV_quality_summary)    

    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run CheckV to evaluate virus genome quality. Finished")
    
    
    # Step 7 Run dRep to get viral species
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run dRep to cluster virus species. In processing...") 
    
    ## Step 7.1 Make gn list for each genus
    scripts.module.get_gn_list_for_genus(genus_cluster_info, args['drep_outdir'], vRhyme_best_bin_dir_modified, vRhyme_unbinned_viral_gn_dir)  

    ## Step 7.2 Run dRep
    viral_genus_genome_list_dir = os.path.join(args['drep_outdir'], 'viral_genus_genome_list')
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-dRep')} python {os.path.join(args['root_dir'],'scripts/run_dRep.py')} {args['drep_outdir']} {viral_genus_genome_list_dir} {args['threads']} 2000 >/dev/null 2>&1")
    species_cluster_info = os.path.join(args['out_dir'], 'Species_cluster_info.txt')
    scripts.module.parse_dRep(args['out_dir'], args['drep_outdir'], species_cluster_info, genus_cluster_info, viral_genus_genome_list_dir)
    
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Run dRep to cluster virus species. Finished") 
    
    
    # Step 8 Taxonomic charaterization
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Conduct taxonomic charaterization. In processing...")  
    
    ## Step 8.1 Run diamond to NCBI RefSeq viral protein db 
    tax_refseq_output = os.path.join(args['out_dir'], 'tax_refseq_output.txt')
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-Tax')} python {os.path.join(args['root_dir'],'scripts/run_Tax_RefSeq.py')} {args['out_dir']} {vRhyme_best_bin_dir_modified} {vRhyme_unbinned_viral_gn_dir} {args['Tax_classification_db']} {pro2viral_gn_map} {args['threads']} {tax_refseq_output}")

    ## Step 8.2 Run hmmsearch to marker VOG HMM db
    vog_marker_table = os.path.join(args['Tax_classification_db'], 'VOG_marker_table.txt')
    tax_vog_output = os.path.join(args['out_dir'], 'tax_vog_output.txt')
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-Tax')} python {os.path.join(args['root_dir'],'scripts/run_Tax_VOG.py')} {vog_marker_table} {args['out_dir']} {vRhyme_best_bin_dir_modified} {vRhyme_unbinned_viral_gn_dir} {args['Tax_classification_db']} {pro2viral_gn_map} {args['threads']} {tax_vog_output}")

    ## Step 8.3 Get taxonomy information from vContact2 result
    tax_vcontact2_output = os.path.join(args['out_dir'], 'tax_vcontact2_output.txt')
    IMGVR_db_map = os.path.join(args['Tax_classification_db'], 'IMGVR_high-quality_phage_vOTU_representatives_pro2viral_gn_map.csv')
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-Tax')} python {os.path.join(args['root_dir'],'scripts/run_Tax_vContact2.py')} {genome_by_genome_file} {IMGVR_db_map} {tax_vcontact2_output}")

    ## Step 8.4 Integrate all taxonomical results
    tax_classification_result = os.path.join(args['out_dir'], 'Tax_classification_result.txt')
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-Tax')} python {os.path.join(args['root_dir'],'scripts/run_Tax_combine.py')} {args['out_dir']} {genus_cluster_info} {tax_classification_result}")
    os.system(f"rm {tax_refseq_output} {tax_vog_output} {tax_vcontact2_output}")    
    
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Conduct taxonomic charaterization. Finished")  
    
        
    # Step 9 Host prediction
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Conduct Host prediction by iPHoP. In processing...")      
    ## Step 9.1 Host prediction by iPHoP
    all_vRhyme_fasta_Nlinked = os.path.join(args['vrhyme_outdir'], 'all_vRhyme_fasta.Nlinked_viral_gn.fasta')
    scripts.module.combine_all_vRhyme_fasta(args['nlinked_viral_gn_dir'], '', all_vRhyme_fasta_Nlinked)
    os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-iPHoP')} python {os.path.join(args['root_dir'],'scripts/run_iPHoP.py')} {all_vRhyme_fasta_Nlinked} {args['iphop_outdir']} {args['iPHoP_db']} {args['threads']} >/dev/null 2>&1")

    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Conduct Host prediction by iPHoP. Finished")  
    
    ## Step 9.2 Host prediction by iPHoP by adding custom MAGs to host db
    if args['custom_MAGs_dir'] != 'none' and args['iPHoP_db_custom_pre'] == 'none':
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Conduct Host prediction by iPHoP using custom MAGs. In processing...")   
               
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-GTDBTk')} python {os.path.join(args['root_dir'],'scripts/add_custom_MAGs_to_host_db__make_gtdbtk_results.py')} {args['out_dir']} {args['custom_MAGs_dir']} {args['threads']} >/dev/null 2>&1")
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-iPHoP')} python {os.path.join(args['root_dir'],'scripts/add_custom_MAGs_to_host_db__add_to_db.py')} {args['out_dir']} {args['custom_MAGs_dir']} {args['iPHoP_db']} {args['iPHoP_db_custom']} >/dev/null 2>&1")
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-iPHoP')} python {os.path.join(args['root_dir'],'scripts/run_iPHoP.py')} {all_vRhyme_fasta_Nlinked} {args['iphop_custom_outdir']} {args['iPHoP_db_custom']} {args['threads']} >/dev/null 2>&1")  

        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Conduct Host prediction by iPHoP using custom MAGs. Finished") 
    elif args['custom_MAGs_dir'] != 'none' and args['iPHoP_db_custom_pre'] != 'none': # iPHoP db custom was provided (by the previous run)   
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Conduct Host prediction by iPHoP using custom MAGs. In processing...") 
    
        os.system(f"conda run -p {os.path.join(args['conda_env_dir'], 'ViWrap-iPHoP')} python {os.path.join(args['root_dir'],'scripts/run_iPHoP.py')} {all_vRhyme_fasta_Nlinked} {args['iphop_custom_outdir']} {args['iPHoP_db_custom_pre']} {args['threads']} >/dev/null 2>&1")                     
    
        time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
        logger.info(f"{time_current} | Conduct Host prediction by iPHoP using custom MAGs. Finished") 

        
    # Step 10 Get virus genome abundance
    os.mkdir(args['viwrap_summary_outdir'])
    os.system(f"mv {os.path.join(args['out_dir'],'*.txt')} {args['viwrap_summary_outdir']}")
    virus_raw_abundance = os.path.join(args['viwrap_summary_outdir'],'Virus_raw_abundance.txt')
    scripts.module.get_virus_raw_abundance(args['mapping_outdir'], vRhyme_best_bin_dir_modified, vRhyme_unbinned_viral_gn_dir, virus_raw_abundance)
    sample2read_info_file = os.path.join(args['viwrap_summary_outdir'],'Sample2read_info.txt')
    virus_normalized_abundance = os.path.join(args['viwrap_summary_outdir'],'Virus_normalized_abundance.txt')
    scripts.module.get_virus_normalized_abundance(args['mapping_outdir'], virus_raw_abundance, virus_normalized_abundance, sample2read_info, sample2read_info_file)
    
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Get virus genome abundance. Finished") 
    
    
    # Step 11 Get all virus sequence information
    ## Step 11.1 Move all virus genome fasta, ffn, and faa files
    viral_gn_dir = os.path.join(args['viwrap_summary_outdir'],'Virus_genomes_files')
    os.mkdir(viral_gn_dir)
    os.system(f'cp {vRhyme_best_bin_dir_modified}/* {viral_gn_dir}')
    os.system(f'cp {vRhyme_unbinned_viral_gn_dir}/* {viral_gn_dir}')
    
    ## Step 11.2 Get VIBRANT lytic and lysogenic information and genome information
    checkv_dict = scripts.module.get_checkv_useful_info(os.path.join(args['checkv_outdir'], 'CheckV_quality_summary.txt'))
    gn2lyso_lytic_result = {}
    if args['identify_method'] == 'vb' or args['identify_method'] == 'vb-vs-dvf' or args['identify_method'] == 'vb-vs':
        gn2lyso_lytic_result = scripts.module.get_gn_lyso_lytic_result(scf2lytic_or_lyso_summary, vRhyme_best_bin_lytic_and_lysogenic_info, viral_gn_dir)
    gn2size_and_scf_no_and_pro_count = scripts.module.get_viral_gn_size_and_scf_no_and_pro_count(viral_gn_dir)
    gn2long_scf2kos = ''
    if args['identify_method'] == 'vb':
        gn2long_scf2kos = scripts.module.get_amg_info_for_vb(args['vibrant_outdir'], Path(args['input_metagenome']).stem, viral_gn_dir)
    elif args['identify_method'] == 'vs' or args['identify_method'] == 'dvf' or args['identify_method'] == 'vb-vs-dvf' or args['identify_method'] == 'vb-vs':
        gn2long_scf2kos = scripts.module.get_amg_info_for_vs_and_dvf(args, viral_gn_dir)
    gn2amg_statistics = scripts.module.get_amg_statistics(gn2long_scf2kos)
    virus_summary_info = os.path.join(args['viwrap_summary_outdir'],'Virus_summary_info.txt')
    scripts.module.get_virus_summary_info(checkv_dict, gn2lyso_lytic_result, gn2size_and_scf_no_and_pro_count, gn2amg_statistics, virus_summary_info) 
    
    ## Step 11.3 Combine host prediction result
    combined_host_pred_to_genome_result = os.path.join(args['viwrap_summary_outdir'],'Host_prediction_to_genome_m90.csv')
    combined_host_pred_to_genus_result = os.path.join(args['viwrap_summary_outdir'],'Host_prediction_to_genus_m90.csv')
    scripts.module.combine_iphop_results(args, combined_host_pred_to_genome_result, combined_host_pred_to_genus_result)
    
    ## Step 11.4 Get virus genome annotation result
    scripts.module.get_virus_genome_annotation_result(args)
    
    ## Step 11.5 Get AMG results
    AMG_dir = os.path.join(args['viwrap_summary_outdir'],'AMG_results')
    os.mkdir(AMG_dir)
    scripts.module.write_down_gn2amg_statistics(AMG_dir, gn2amg_statistics) # Write down the gn2amg_statistics dict    
    virus_annotation_result_file = os.path.join(args['viwrap_summary_outdir'],'Virus_annotation_results.txt')
    amg_pro2info = scripts.module.get_amg_pro_info(AMG_dir, virus_annotation_result_file, args['VIBRANT_db']) # Get the amg_pro2info dict
    scripts.module.write_down_amg_pro2info(AMG_dir, amg_pro2info) # Write down the amg_pro2info dict
    scripts.module.pick_amg_pro(AMG_dir, amg_pro2info, viral_gn_dir) # Pick the AMG proteins and write down the AMG proteins
    
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Get virus sequence information. Finished")  
     
   
    # Step 12 Visualize the result
    scripts.module.generate_result_visualization_inputs(args['viwrap_visualization_outdir'], args['viwrap_summary_outdir'], args['VIBRANT_db'])
    visualization_input_dir = os.path.join(args['viwrap_visualization_outdir'],'Result_visualization_inputs')
    os.system(f"python {os.path.join(args['root_dir'],'scripts/run_Visualization.py')} -i {visualization_input_dir} -r {args['out_dir']} -o '09_Virus_statistics_visualization/Result_visualization_outputs'")
    
    time_current = f"[{str(datetime.now().replace(microsecond=0))}]"
    logger.info(f"{time_current} | Visualize the result. Finished")  
    
    
    end_time = datetime.now().replace(microsecond=0)
    duration = end_time - start_time
    logger.info(f"The total running time is {duration} (in \"hr:min:sec\" format)")  
   
