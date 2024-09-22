from pydantic.v1 import BaseModel, Field
from typing import List, Optional
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from query_data import query_rag
from langchain_together import Together
import textwrap
import json
import os

together_api_key = "f79744841a9d211621a12f924b810dab2a71a48375b78a094372fb9ae3c9fbe6"

def wrap_text(text, width=20):
    return '\n'.join(textwrap.wrap(text, width=width))

class InfoNode(BaseModel):
    information: str = Field(description="Relevant information about the topic")
    emoji: str = Field(description="A relevant emoji for this information")

class SubTopicNode(BaseModel):
    subtopic: str = Field(description="A subtopic of the main topic")
    emoji: str = Field(description="A relevant emoji for this subtopic")
    children: List[InfoNode] = Field(description="A list of 2-3 information nodes for this subtopic")

class TopicNode(BaseModel):
    topic: str = Field(description="The main topic of the node")
    emoji: str = Field(description="A relevant emoji for this topic")
    summary: str = Field(description="A brief summary of the topic")
    children: List[SubTopicNode] = Field(description="A list of 2-3 subtopic nodes")

class MindMap(BaseModel):
    central_topic: str = Field(description="The central topic of the mind map")
    central_emoji: str = Field(description="A relevant emoji for the central topic")
    topicNodes: List[TopicNode] = Field(description="A list of 3-4 main topic nodes")

def generate_mindmap(topic: str, chat_id: str) -> dict:
    context, sources = query_rag(f"Provide detailed information about {topic}", chat_id)
    model = Together(
        model="meta-llama/Meta-Llama-3-8B-Instruct-Lite",
        temperature=0.7,
        max_tokens=2048,
        top_k=50,
        together_api_key=together_api_key
    )

    parser = PydanticOutputParser(pydantic_object=MindMap)
    mindmap_prompt = PromptTemplate(
        template="""Based on the following information about {topic}, generate a detailed mind map with the following structure:
        - A central topic with an emoji
        - 3-4 main topic nodes, each with:
          - An emoji
          - A brief summary
          - 2-3 subtopic nodes, each with:
            - An emoji
            - 2-3 information nodes
        
        Ensure all emojis are relevant to their respective topics or information.
        DO NOT USE JSON references like $ref or #defs. Provide only the actual content for each field.
        
        Information about {topic}:
        {context}
        
        {format_instructions}""",
        input_variables=["topic", "context"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
   
    try:
        mindmap_output = model.invoke(mindmap_prompt.format(topic=topic, context=context))
        mindmap = parser.parse(mindmap_output)
    except ValueError as e:
        if "$ref" in str(e) or "#defs" in str(e):
            strict_prompt = PromptTemplate(
                template="""Based on the following information about {topic}, generate a detailed mind map with the following structure:
                - A central topic with an emoji
                - 3-4 main topic nodes, each with:
                  - An emoji
                  - A brief summary
                  - 2-3 subtopic nodes, each with:
                    - An emoji
                    - 2-3 information nodes
                
                Ensure all emojis are relevant to their respective topics or information.
                DO NOT USE ANY JSON SCHEMA REFERENCES like '#defs' or '$ref'. Provide only the actual content for each field.
                
                Information about {topic}:
                {context}
                
                {format_instructions}
                If mentioned by mistake, still don't use $defs or $ref""",
                input_variables=["topic", "context"],
                partial_variables={"format_instructions": parser.get_format_instructions()}
            )
            mindmap_output = model.invoke(strict_prompt.format(topic=topic, context=context))
            mindmap = parser.parse(mindmap_output)
        else:
            raise

    network_data = convert_to_network_data(mindmap)
    return network_data

def convert_to_network_data(mindmap: MindMap) -> dict:
    nodes = []
    edges = []
    node_id = 1

    # Central topic
    nodes.append({
        "id": node_id,
        "label": f"{mindmap.central_emoji} {wrap_text(mindmap.central_topic)}",
        "group": "central"
    })
    central_id = node_id
    node_id += 1

    for topic_node in mindmap.topicNodes:
        topic_id = node_id
        nodes.append({
            "id": topic_id,
            "label": f"{topic_node.emoji} {wrap_text(topic_node.topic)}\n{wrap_text(topic_node.summary)}",
            "group": "topic"
        })
        edges.append({"from": central_id, "to": topic_id})
        node_id += 1

        for subtopic_node in topic_node.children:
            subtopic_id = node_id
            nodes.append({
                "id": subtopic_id,
                "label": f"{subtopic_node.emoji} {wrap_text(subtopic_node.subtopic)}",
                "group": "subtopic"
            })
            edges.append({"from": topic_id, "to": subtopic_id})
            node_id += 1

            for info_node in subtopic_node.children:
                nodes.append({
                    "id": node_id,
                    "label": f"{info_node.emoji} {wrap_text(info_node.information)}",
                    "group": "info",
                    "shape": "box",
                    "size": 30,
                    "font": {"size": 14},
                    "margin": 10
                })
                edges.append({"from": subtopic_id, "to": node_id})
                node_id += 1

    return {"nodes": nodes, "edges": edges}
