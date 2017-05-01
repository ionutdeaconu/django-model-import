import tablib
from django.forms import modelform_factory

from .caches import SimpleDictCache


class ModelImporter:
    """ A base class which parses and processes a CSV import, and handles the priming of any required caches. """
    def __init__(self, modelimportform):
        self.instances = []
        self.errors = []
        self.modelimportform = modelimportform
        self.model = modelimportform.Meta.model

    def parse(self, data):
        """ Parse the imported data. """
        dataset = tablib.Dataset()
        dataset.csv = data
        return dataset

    def get_modelimport_form_class(self, fields):
        """ Return a modelform for use with this data.

        We use a modelform_factory to dynamically limit the fields on the import,
        otherwise the absence of a value can be taken as false for boolean fields,
        where as we want the model's default value to kick in.
        """
        return modelform_factory(
            self.model,
            form=self.modelimportform,
            fields=fields,
        )

    def process(self, data, commit=False):
        # Set up a cache context which will be filled by the Cached fields
        caches = SimpleDictCache()

        # Parse the CSV
        dataset = self.parse(data)

        # Prepare
        headers = dataset.headers
        ModelImportForm = self.get_modelimport_form_class(fields=headers)
        importresult = ImportResultSet(import_headers=headers)

        # Start processing
        for i, row in enumerate(dataset.dict, start=1):
            instance = None
            errors = []

            form = ModelImportForm(row, caches)
            if form.is_valid():
                instance = form.save(commit=commit)
            else:
                errors = form.errors.items()

            importresult.append(i, row, errors, instance)

        return importresult


class ImportResultSet:
    """ Hold all imported results. """
    import_headers = None
    results = None

    def __init__(self, import_headers):
        self.results = []
        self.import_headers = import_headers

    def __str__(self):
        return '{} {}'.format(self.import_headers, self.results)

    def append(self, index, row, errors, instance):
        self.results.append(
            ImportResultRow(self, index, row, errors, instance)
        )

    def get_import_headers(self):
        return self.import_headers

    def get_results(self):
        return self.results

    def get_errors(self):
        return [(row.linenumber, row.errors) for row in self.results if not row.is_valid()]


class ImportResultRow:
    """ Hold the result of an imported row. """
    resultset = None
    linenumber = None
    row = None
    errors = None
    instance = None

    def __init__(self, resultset, linenumber, row, errors, instance):
        self.resultset = resultset
        self.linenumber = linenumber
        self.row = row
        self.errors = errors
        self.instance = instance

    def __str__(self):
        return '{} {}'.format(self.linenumber, self.row)

    def get_instance_values(self):
        return [getattr(self.instance, header) for header in self.resultset.import_headers]

    def is_valid(self):
        return len(self.errors) == 0
