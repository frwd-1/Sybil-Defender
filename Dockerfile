# Build stage: compile Python dependencies
FROM ubuntu:focal as builder

RUN apt-get update -y && apt-get upgrade -y

# Install software-properties-common to add new repository
RUN apt-get install -y software-properties-common

# Add the deadsnakes PPA, which contains newer versions of Python
RUN add-apt-repository ppa:deadsnakes/ppa

# Install Python 3.10 and Python dev packages
RUN apt-get install -y python3.10 python3.10-dev python3.10-venv python3.10-distutils

# Install build dependencies for C extensions
RUN apt-get install -y build-essential libffi-dev libssl-dev

# Use ensurepip to install pip for Python 3.10
RUN python3.10 -m ensurepip

# Update pip using python3.10 explicitly
RUN python3.10 -m pip install --upgrade pip

COPY requirements.txt ./

# Install your requirements using python3.10 explicitly
RUN python3.10 -m pip install --user -r requirements.txt --no-cache-dir

# Final stage: set up environment with Node.js and copy over Python dependencies
FROM ubuntu:focal

# Install required packages
RUN apt-get update -y && apt-get upgrade -y
RUN apt-get install -y curl gnupg software-properties-common

# Add the deadsnakes PPA in the final stage too
RUN add-apt-repository ppa:deadsnakes/ppa

# Install Python 3.10
RUN apt-get install -y python3.10

# Update alternatives to use python3.10 as the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1

# Install Node.js
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get -y install nodejs

COPY --from=builder /root/.local /root/.local

# Set the PATH to include python and local pip binaries
ENV PATH=/root/.local/bin:$PATH
ENV NODE_ENV=production

# Uncomment the following line to enable agent logging
LABEL "network.forta.settings.agent-logs.enable"="true"

WORKDIR /app
COPY .env ./
COPY ./src ./src
COPY package*.json ./
COPY LICENSE.md ./

# Install Node dependencies
RUN npm ci --production

CMD ["npm", "run", "start:prod"]
