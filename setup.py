from setuptools import setup

setup(
    name='TracAutoCompleteTicketFieldPlugin',
    #description='',
    #keywords='',
    #url='',
    version='0.1',
    #license='',
    #author='',
    #author_email='',
    #long_description="",
    packages=['autocomplticketfield'],
    package_data={
        'autocomplticketfield': [
            'htdocs/js/*.js',
            'htdocs/css/*.css',
        ]
    },
    entry_points={
        'trac.plugins': [
            'autocomplticketfield.web_ui = autocomplticketfield.web_ui'
        ]
    }
)
