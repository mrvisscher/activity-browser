# -*- coding: utf-8 -*-
import brightway2 as bw

def cleanup():
    n_dir = bw.projects.purge_deleted_directories()
    print('Deleted {} unused project directories!'.format(n_dir))
