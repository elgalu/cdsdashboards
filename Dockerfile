ARG BASE_IMAGE=jupyterhub/jupyterhub:1.2
FROM $BASE_IMAGE

RUN python3 -m pip install setuptools notebook dockerspawner

RUN mkdir /tmp/cdsdashboard_current

ADD . /tmp/cdsdashboard_current/

COPY ./e2e/setup-helper/startup-script.sh /usr/local/bin/startup-script.sh

RUN cd /tmp/cdsdashboard_current \
        && python3 setup.py sdist \
        && python3 -m pip install ./`ls dist/cdsdashboards-*.tar.gz` \
        && cd .. && rm -rf ./cdsdashboard_current

RUN pip install streamlit

RUN pip install dash plotlydash-tornado-cmd

RUN pip install bokeh panel bokeh-root-cmd

ENTRYPOINT ["/usr/local/bin/startup-script.sh"]

CMD ["jupyterhub"]

LABEL com.containds.e2etest="image"
