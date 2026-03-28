from owlready2 import *

# ----------------------------
# Load ontology
# ----------------------------
onto = get_ontology("src/reason/family.owl").load()

print("=== Classes disponibles ===")
for cls in onto.classes():
    print(f"  {cls.name}")

# ----------------------------
# Create oldPerson class
# ----------------------------
with onto:
    class oldPerson(onto.Person):
        pass

# ----------------------------
# SWRL Rule (documented):
# Person(?p) ^ age(?p, ?a) ^ swrlb:greaterThan(?a, 60) -> oldPerson(?p)
# ----------------------------
SWRL_RULE = "Person(?p), age(?p, ?a), swrlb:greaterThan(?a, 60) -> oldPerson(?p)"
print(f"\n=== Règle SWRL ===")
print(f"  {SWRL_RULE}")

# ----------------------------
# Apply rule manually (OWLReady2 does not support swrlb built-ins natively)
# Equivalent to running a SWRL reasoner
# ----------------------------
print("\n=== Application de la règle ===")
with onto:
    for person in onto.Person.instances():
        age_val = person.age
        if isinstance(age_val, list):
            age_val = age_val[0] if age_val else None
        if age_val is not None and int(age_val) > 60:
            if onto.oldPerson not in person.is_a:
                person.is_a.append(onto.oldPerson)
                print(f"  -> {person.name} (age={age_val}) classifié comme oldPerson")

# ----------------------------
# Results
# ----------------------------
print("\n=== Résultat : instances oldPerson inférées ===")
old_persons = list(onto.oldPerson.instances())
for p in old_persons:
    print(f"  {p.name} — age: {p.age}")

print(f"\nTotal oldPerson inférés : {len(old_persons)}")

print("\n=== Toutes les personnes ===")
for p in onto.Person.instances():
    cls = [c.name for c in p.is_a if hasattr(c, "name")]
    print(f"  {p.name} — age: {p.age} — classes: {cls}")
