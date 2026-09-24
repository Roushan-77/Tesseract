# Tesseract

## AI-Powered Criminal Network Intelligence Platform

Tesseract is an investigator intelligence platform designed to transform fragmented investigation data into connected, explainable intelligence.

It brings evidence processing, entity extraction, entity resolution, knowledge graphs, timeline analysis, network intelligence, evidence integrity, access control, and investigation reporting into a unified workspace.

## Overview

Criminal investigations often involve large volumes of disconnected information spread across documents, communication records, financial transactions, surveillance reports, vehicle records, and field intelligence.

Tesseract helps investigators connect these sources and explore relationships, events, patterns, and supporting evidence from a single investigation workspace.

The platform is designed around three principles:

- Evidence-backed intelligence
- Human-in-the-loop investigation
- Traceable and accountable workflows

## Core Capabilities

### Evidence Intelligence

Process multiple investigation data sources including:

- FIRs and investigation reports
- PDF and image documents
- Communication records
- Financial transactions
- Vehicle movement records
- Structured datasets
- Field intelligence

The system extracts relevant entities and information while preserving the relationship between extracted information and its source evidence.

### Multilingual Document Processing

The document processing pipeline supports multilingual investigation workflows using OCR and NLP.

Current capabilities include:

- English and Hindi OCR
- Named entity extraction
- Phone number extraction
- Vehicle number extraction
- Case and date extraction
- Financial information extraction
- Location and organization extraction
- Structured data parsing

### Entity Resolution

Different records can refer to the same entity using different names, formats, or attributes.

Tesseract provides confidence-based matching suggestions that investigators can review before confirming or rejecting a relationship.

The investigator remains in control of the final resolution decision.

### Criminal Knowledge Graph

Tesseract connects entities and relationships into an interactive investigation graph.

The graph can represent:

- People
- Organizations
- Phone numbers
- Vehicles
- Locations
- Events
- Transactions
- Evidence

Relationships retain supporting information so investigators can trace intelligence back to its underlying evidence.

### Network Intelligence

The connected graph can be used to examine:

- Highly connected entities
- Communication hubs
- Important organizations
- Network relationships
- Connected resources
- Supporting evidence
- Structural patterns

### Timeline Analysis

Investigation events can be examined chronologically.

The timeline can bring together:

- Calls
- Meetings
- Financial transfers
- Locations
- Vehicle movements
- Other timestamped events

### Intelligence and Anomaly Detection

Tesseract surfaces investigation signals from connected data, including:

- Communication activity spikes
- Unusual financial activity
- Temporal patterns
- Network relationships
- Structurally important entities

These signals are intended to support investigators rather than replace investigative judgment.

### Evidence Integrity

Evidence integrity is supported through cryptographic hashing and verification.

The integrity layer provides:

- SHA-256 hashing
- Evidence verification
- Tamper detection
- Integrity status
- Verification timestamps
- Ledger metadata

Evidence itself remains stored separately from its integrity metadata.

### Investigator Flagging

Investigators can flag evidence, entities, events, or intelligence findings for further review.

Flags can contain:

- Reason
- Investigator
- Timestamp
- Review status

### Role-Based Access Control

The platform includes role-aware access controls for sensitive investigation data.

Capabilities include:

- Investigator authentication
- Case assignments
- Restricted cases
- Access requests
- Grant and deny workflows
- Protected evidence
- Protected intelligence endpoints

### Audit Trail

Important investigation actions are recorded for accountability.

Examples include:

- Case access
- Evidence access
- Evidence processing
- Integrity verification
- Graph access
- Timeline access
- Intelligence access
- Access requests
- Evidence uploads
- Flagging actions
- Login activity

### Investigation Reports

Investigation information can be compiled into PDF reports containing relevant case information, evidence, entities, relationships, timelines, intelligence findings, flags, integrity information, and audit information.

## Architecture

```text
                Investigation Data
                       |
                       v
               Evidence Ingestion
                       |
                       v
              OCR / NLP / Parsing
                       |
                       v
                Entity Extraction
                       |
                       v
                Entity Resolution
                       |
                       v
                Knowledge Graph
                       |
          +------------+------------+
          |            |            |
          v            v            v
       Timeline    Intelligence   Integrity
       Analysis      Analysis     Verification
          |            |            |
          +------------+------------+
                       |
                       v
             Investigator Workspace
                       |
          +------------+------------+
          |            |            |
          v            v            v
        Flags       Audit Trail    Reports