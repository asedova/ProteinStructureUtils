import uuid
import os
import logging
import shutil

from DataFileUtil.DataFileUtilClient import DataFileUtil
from KBaseReport.KBaseReportClient import KBaseReport


class PDBUtil:

    def _validate_import_pdb_file_params(self, params):
        """
        _validate_import_matrix_from_excel_params:
            validates params passed to import_matrix_from_excel method
        """
        # check for required parameters
        for p in ['structure_name', 'workspace_name']:
            if p not in params:
                raise ValueError('"{}" parameter is required, but missing'.format(p))

        if params.get('input_file_path'):
            file_path = params.get('input_file_path')
        elif params.get('input_shock_id'):
            file_path = self.dfu.shock_to_file(
                {'shock_id': params['input_shock_id'],
                 'file_path': self.scratch}).get('file_path')
        elif params.get('input_staging_file_path'):
            file_path = self.dfu.download_staging_file(
                        {'staging_file_subdir_path': params.get('input_staging_file_path')}
                        ).get('copy_file_path')
        else:
            error_msg = "Must supply either a input_shock_id or input_file_path "
            error_msg += "or input_staging_file_path"
            raise ValueError(error_msg)

        return file_path, params.get('workspace_name'), params.get('structure_name')

    def _file_to_data(self, file_path):
        """Do the PDB conversion"""
        return {}

    def _pdb_shock_id(self, obj_ref):
        obj_data = self.dfu.get_objects(
            {"object_refs": [obj_ref]})['data'][0]
        return obj_data.get('pdb_ref')

    def _upload_to_shock(self, file_path):
        """
        _upload_to_shock: upload target file to shock using DataFileUtil
        """
        logging.info('Start uploading file to shock: {}'.format(file_path))

        file_to_shock_params = {
            'file_path': file_path,
            'pack': 'gzip'
        }
        shock_id = self.dfu.file_to_shock(file_to_shock_params).get('shock_id')

        return shock_id

    def _generate_search_html_report(self, header_str, table_str):
        #Included as an example

        html_report = list()

        output_directory = os.path.join(self.scratch, str(uuid.uuid4()))
        self._mkdir_p(output_directory)
        result_file_path = os.path.join(output_directory, 'search.html')

        shutil.copy2(os.path.join(os.path.dirname(__file__), 'templates', 'kbase_icon.png'),
                     output_directory)
        shutil.copy2(os.path.join(os.path.dirname(__file__), 'templates', 'search_icon.png'),
                     output_directory)

        with open(result_file_path, 'w') as result_file:
            with open(os.path.join(os.path.dirname(__file__), 'templates', 'search_template.html'),
                      'r') as report_template_file:
                report_template = report_template_file.read()
                report_template = report_template.replace('//HEADER_STR', header_str)
                report_template = report_template.replace('//TABLE_STR', table_str)
                result_file.write(report_template)

        report_shock_id = self.dfu.file_to_shock({'file_path': output_directory,
                                                  'pack': 'zip'})['shock_id']

        html_report.append({'shock_id': report_shock_id,
                            'name': os.path.basename(result_file_path),
                            'label': os.path.basename(result_file_path),
                            'description': 'HTML summary report for Search Matrix App'})

        return html_report

    def _generate_report(self, pdb_obj_ref, workspace_name):
        """
        _generate_report: generate summary report
        """
        # included as an example. Replace with your own implementation
        # output_html_files = self._generate_search_html_report(header_str, table_str)

        report_params = {'message': 'You uploaded a PDB file!',
                         #'html_links': output_html_files,
                         #'direct_html_link_index': 0,
                         'objects_created': [{'ref': pdb_obj_ref,
                                              'description': 'Imported PDB'}],
                         'workspace_name': workspace_name,
                         'report_object_name': 'import_pdb_from_staging_' + str(uuid.uuid4())}

        kbase_report_client = KBaseReport(self.callback_url, token=self.token)
        output = kbase_report_client.create_extended_report(report_params)

        report_output = {'report_name': output['name'], 'report_ref': output['ref']}

        return report_output

    def __init__(self, config):
        self.callback_url = config['SDK_CALLBACK_URL']
        self.scratch = config['scratch']
        self.token = config['KB_AUTH_TOKEN']
        self.dfu = DataFileUtil(self.callback_url)

    def import_pdb_file(self, params):

        file_path, workspace_name, pdb_name = self._validate_import_pdb_file_params(params)

        if not isinstance(workspace_name, int):
            workspace_id = self.dfu.ws_name_to_id(workspace_name)
        else:
            workspace_id = workspace_name

        data = self._file_to_data(file_path)
        if params.get('description'):
            data['description'] = params['description']

        info = self.dfu.save_objects([{
            'obj_type': 'KBaseStructure.ProteinStructure',
            'obj_name': pdb_name,
            'data': data,
            'workspace_name': workspace_id}])[0]
        obj_ref = "%s/%s/%s" % (info[6], info[0], info[4])

        returnVal = {'structure_obj_ref': obj_ref}

        report_output = self._generate_report(obj_ref, workspace_name)

        returnVal.update(report_output)

        return returnVal

    def export_pdb(self, params):
        if "obj_ref" not in params:
            raise ValueError("obj_ref not in supplied params")

        return self._pdb_shock_id(params['obj_ref'])

    def structure_to_pdb_file(self, params):
        if "obj_ref" not in params:
            raise ValueError("obj_ref not in supplied params")
        if "destination_dir" not in params:
            raise ValueError("destination_dir not in supplied params")

        shock_id = self._pdb_shock_id(params['obj_ref'])
        file_path = self.dfu.shock_to_file({
            'handle_id': shock_id,
            'file_path': params['destination_dir'],
            'unpack': 'uncompress'
        })['file_path']

        return {'file_path': file_path}


