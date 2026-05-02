FROM eclipse-temurin:25-jdk

ARG MAVEN_VERSION=3.9.9

ENV DEBIAN_FRONTEND=noninteractive

# Install Python and wget
RUN apt-get update && apt-get install -y \
        python3 python3-venv \
        wget \
    && rm -rf /var/lib/apt/lists/*

# Install Maven 3.9
RUN wget -q https://archive.apache.org/dist/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz \
        -O /tmp/maven.tar.gz \
    && tar -xzf /tmp/maven.tar.gz -C /opt/ \
    && ln -s /opt/apache-maven-${MAVEN_VERSION} /opt/maven \
    && rm /tmp/maven.tar.gz

ENV PATH="/opt/maven/bin:${PATH}"

# Copy SimpleChat source and install Python dependencies in an isolated venv
COPY requirements.txt /opt/simplechat/
COPY chat.py           /opt/simplechat/
COPY tools/__init__.py            /opt/simplechat/tools/
COPY tools/base.py                /opt/simplechat/tools/
COPY tools/registry.py            /opt/simplechat/tools/
COPY tools/time_tool.py           /opt/simplechat/tools/
COPY tools/python_exec_tool.py    /opt/simplechat/tools/
COPY tools/command_line_tool.py   /opt/simplechat/tools/
COPY tools/configurable_command_tool.py /opt/simplechat/tools/
COPY tools/write_file_tool.py           /opt/simplechat/tools/
COPY tools/edit_file_tool.py           /opt/simplechat/tools/

RUN python3 -m venv /opt/simplechat-venv \
    && /opt/simplechat-venv/bin/pip install --upgrade pip \
    && /opt/simplechat-venv/bin/pip install -r /opt/simplechat/requirements.txt

# Install simplechat wrapper so it can be called without the python prefix
RUN printf '#!/bin/bash\nexec /opt/simplechat-venv/bin/python /opt/simplechat/chat.py "$@"\n' \
        > /usr/local/bin/simplechat \
    && chmod +x /usr/local/bin/simplechat

RUN mkdir /workdir
WORKDIR /workdir

CMD ["/bin/bash"]
