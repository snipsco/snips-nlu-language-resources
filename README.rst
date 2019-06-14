Snips NLU language resources
============================

This repository contains language specific resources that are required by the `Snips NLU`_ library.

The way resources are packaged is largely inspired from `spaCy`_.

Usage
-----

Install the `Snips NLU`_ library with ``pip install snips-nlu`` and then run one of the following commands to fetch the language resources:

.. code-block:: sh

    python -m snips_nlu download [language]

Or simply:

.. code-block:: sh
    
    snips-nlu download [language]

.. _Snips NLU: https://github.com/snipsco/snips-nlu
.. _spacy: https://github.com/explosion/spaCy-models