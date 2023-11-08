# Build stage: compile Python dependencies
FROM python:3.9-alpine as builder
RUN apk update
RUN apk add alpine-sdk
RUN python3 -m pip install --upgrade pip
COPY requirements.txt ./
RUN python3 -m pip install --user -r requirements.txt

# Final stage: copy over Python dependencies and install production Node dependencies
FROM node:12-alpine
# this python version should match the build stage python version
# Install dependencies for building Python
RUN apk add --no-cache git bash gcc musl-dev openssl-dev libffi-dev make patch


# Install pyenv and required dependencies in one layer
RUN apk add --no-cache git bash gcc musl-dev openssl-dev libffi-dev make patch && \
    git clone https://github.com/pyenv/pyenv.git ~/.pyenv && \
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc && \
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc && \
    echo 'eval "$(pyenv init --path)"' >> ~/.bashrc && \
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc

ENV PYENV_ROOT /root/.pyenv
ENV PATH /root/.pyenv/shims:/root/.pyenv/bin:$PATH

# Install the specific Python version
RUN pyenv install 3.9.0 && pyenv global 3.9.0

COPY --from=builder /root/.local /root/.local

ENV PATH=/root/.local:$PATH
ENV NODE_ENV=production
# Uncomment the following line to enable agent logging
LABEL "network.forta.settings.agent-logs.enable"="true"
WORKDIR /app
COPY ./src ./src
COPY package*.json ./
COPY LICENSE.md ./
RUN npm ci --production
CMD [ "npm", "run", "start:prod" ]