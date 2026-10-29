import json
from pathlib import Path
from backend.app.core import database
from backend.app.core.security import get_password_hash
from backend.app.models.institution import Institution
from backend.app.models.user import User
from backend.app.models.application import ChecklistItem
from backend.app.models.compliance import ComplianceRule
from backend.app.models.audit import AuditLog

def seed_database(db_session=None):
    print("Creating all database tables...")
    database.Base.metadata.create_all(bind=database.engine)
    db = db_session if db_session is not None else database.SessionLocal()

    try:
        # 1. Seed Institutions
        inst1 = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1001").first()
        if not inst1:
            inst1 = Institution(
                name="Apex Institute of Technology",
                trust_name="Apex Education Trust",
                address="Sector 14, Plot 8, Navi Mumbai",
                state="Maharashtra",
                aicte_id="AICTE-1-1001"
            )
            db.add(inst1)

        inst2 = db.query(Institution).filter(Institution.aicte_id == "AICTE-1-1002").first()
        if not inst2:
            inst2 = Institution(
                name="Zenith College of Engineering",
                trust_name="Zenith Foundation",
                address="Outer Ring Road, Marathahalli, Bengaluru",
                state="Karnataka",
                aicte_id="AICTE-1-1002"
            )
            db.add(inst2)

        db.commit()

        # 2. Seed Users
        users_to_seed = [
            {
                "email": "inst1@aicte.gov.in",
                "password": "Demo@Password123",
                "role": "institution",
                "institution_id": inst1.id,
                "full_name": "Apex Tech Dean (Applicant 1)"
            },
            {
                "email": "inst2@aicte.gov.in",
                "password": "Demo@Password123",
                "role": "institution",
                "institution_id": inst2.id,
                "full_name": "Zenith College Principal (Applicant 2)"
            },
            {
                "email": "official@aicte.gov.in",
                "password": "Demo@Password123",
                "role": "official",
                "institution_id": None,
                "full_name": "Dr. S. K. Sharma (AICTE Verification Officer)"
            },
            {
                "email": "admin@aicte.gov.in",
                "password": "Demo@Password123",
                "role": "admin",
                "institution_id": None,
                "full_name": "Council Administrator"
            },
            {
                "email": "auditor@aicte.gov.in",
                "password": "Demo@Password123",
                "role": "auditor",
                "institution_id": None,
                "full_name": "Rajesh Kumar (Internal Auditor)"
            }
        ]

        for u in users_to_seed:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if not existing:
                new_user = User(
                    email=u["email"],
                    hashed_password=get_password_hash(u["password"]),
                    role=u["role"],
                    institution_id=u["institution_id"],
                    full_name=u["full_name"],
                    is_active=True
                )
                db.add(new_user)
                print(f"Seeded user: {u['email']} [{u['role']}]")

        db.commit()

        # 3. Seed Checklist Items
        checklists_path = Path(__file__).resolve().parent.parent / "rules" / "checklists.json"
        if checklists_path.exists():
            with open(checklists_path, "r", encoding="utf-8") as f:
                checklists_data = json.load(f)
            
            for item in checklists_data:
                exists = db.query(ChecklistItem).filter(
                    ChecklistItem.application_type == item["application_type"],
                    ChecklistItem.doc_type == item["doc_type"]
                ).first()
                if not exists:
                    db.add(ChecklistItem(
                        application_type=item["application_type"],
                        doc_type=item["doc_type"],
                        mandatory=item["mandatory"],
                        validity_required=item["validity_required"],
                        description=item["description"]
                    ))
            db.commit()
            print("Seeded checklist items.")

        # 4. Seed Compliance Rules
        compliance_path = Path(__file__).resolve().parent.parent / "rules" / "compliance_rules.json"
        if compliance_path.exists():
            with open(compliance_path, "r", encoding="utf-8") as f:
                compliance_data = json.load(f)

            for rule in compliance_data:
                exists = db.query(ComplianceRule).filter(
                    ComplianceRule.rule_key == rule["rule_key"],
                    ComplianceRule.version == rule["version"]
                ).first()
                if not exists:
                    db.add(ComplianceRule(
                        rule_key=rule["rule_key"],
                        name=rule["name"],
                        clause=rule["clause"],
                        source=rule["source"],
                        program=rule["program"],
                        parameters=rule["parameters"],
                        check_type=rule["check_type"],
                        version=rule["version"],
                        active=rule["active"],
                        verified_against_handbook=rule["verified_against_handbook"],
                        on_missing_data=rule["on_missing_data"]
                    ))
            db.commit()
            print("Seeded compliance rules.")

        # 5. Seed Synthetic Scenarios A-I
        from backend.scripts.seed_sample_scenarios import seed_sample_scenarios
        seed_sample_scenarios(db)

        # 6. Audit Log Seed Entry
        db.add(AuditLog(
            actor_id=None,
            actor_role="system",
            action="database_seed",
            entity_type="system",
            entity_id=None,
            before_state=None,
            after_state={"status": "database_seeded_successfully"}
        ))
        db.commit()
        print("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
