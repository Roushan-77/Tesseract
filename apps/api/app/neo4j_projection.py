from .config import settings


def rebuild_projection(graph: dict) -> dict:
    if not settings.neo4j_uri or not settings.neo4j_password:
        return {"status": "SKIPPED", "reason": "NEO4J_URI and NEO4J_PASSWORD are not configured"}
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password))
    try:
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            for node in graph["nodes"]:
                session.run("MERGE (n:Entity {stableId: $id}) SET n.type=$type, n.label=$label, n.properties=$properties", id=node["id"], type=node["type"], label=node["label"], properties=node.get("properties", {}))
            for edge in graph["edges"]:
                session.run("MATCH (a {stableId: $source}), (b {stableId: $target}) MERGE (a)-[r:OBSERVED {stableId: $id}]->(b) SET r.type=$type, r.confidence=$confidence, r.evidenceIds=$evidenceIds, r.sourceRow=$sourceRow, r.sourceFields=$sourceFields", id=edge["id"], source=edge["source"], target=edge["target"], type=edge["type"], confidence=edge["confidence"], evidenceIds=edge.get("evidenceIds", []), sourceRow=edge.get("sourceRow"), sourceFields=edge.get("sourceFields", []))
        return {"status": "COMPLETED", "nodes": len(graph["nodes"]), "edges": len(graph["edges"])}
    finally:
        driver.close()
