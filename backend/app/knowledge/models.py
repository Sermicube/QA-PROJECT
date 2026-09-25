"""Labels y tipos de relaciones del grafo Neo4j (RF-60 a RF-63).

No hay tablas Postgres en este módulo; el grafo vive completamente en Neo4j.
"""

# Nodos
NODE_MODULE = "Module"
NODE_FEATURE = "Feature"
NODE_RULE = "ValidationRule"
NODE_MESSAGE = "ErrorMessage"
NODE_CASE = "TestCase"
NODE_CERT = "Certification"
NODE_TERM = "Term"

# Relaciones
REL_COVERS = "COVERS"
REL_HAS_CASE = "HAS_CASE"
REL_VALIDATES = "VALIDATES"
REL_IN_MODULE = "IN_MODULE"
REL_TRIGGERS = "TRIGGERS_MESSAGE"
REL_SYNONYM = "SYNONYM"
