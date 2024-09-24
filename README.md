Sem is a semantic code search tool using the all-MiniLM-L6-v2 model for embeddings and FAISS as the vector database.

Embeddings are generated and stored locally in ~.sem/index/. None of your code leaves your computer.

# Introduction

This codebase is made up of a VsCode extension written in Typescript called semsearch, as well as a code search tool called semvector built using Python.

## Semsearch

Semsearch provides an interface through which you can index and query your codebase.

## Semvector

Semvector creates a chunked dictionary representation of a codebase, which is then passed off to a local model to generate embeddings. These embeddings can then be queried against to semantically search your codebase.

# Install

Sem is not currently available in the VsCode extension store as, well, it needs some work. I mean don't get me wrong, it works, but it can be a lot better.
