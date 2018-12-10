FROM jupyter/minimal-notebook:14fdfbf9cfc1

USER root

RUN apt-get update \
  && apt-get install -yq openssh-server

ADD . /tmp/ssh
RUN pip install -e /tmp/ssh
RUN python -mssh_kernel.install

USER jovyan
