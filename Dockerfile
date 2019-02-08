FROM jupyter/minimal-notebook:14fdfbf9cfc1

USER root

RUN apt-get update \
  && apt-get install -yq openssh-server

USER jovyan

ADD --chown=jovyan:users . /tmp/ssh

RUN pip install -e /tmp/ssh

RUN python -msshkernel install --sys-prefix
