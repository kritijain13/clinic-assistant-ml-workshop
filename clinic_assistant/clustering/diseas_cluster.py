from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from clinic_assistant.database.models import MedicalHistory, DiseaseGroup


def get_medical_history(db: Session):

    records = db.query(MedicalHistory).all()

    return records


def prepare_patient_text(records):

    patient_data = []

    for record in records:

        text = (
            f"{record.problem or ''} "
            f"{record.diagnosis or ''} "
            f"{record.notes or ''}"
        )

        patient_data.append({
            "patient_id": record.patient_id,
            "text": text
        })

    return patient_data


def create_vectors(patient_data):

    texts = [item["text"] for item in patient_data]

    vectorizer = TfidfVectorizer()

    X = vectorizer.fit_transform(texts)

    return X, vectorizer


def create_clusters(X, n_clusters=3):

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    labels = kmeans.fit_predict(X)

    return labels, kmeans


def group_patients(patient_data, labels):

    clusters = {}

    for item, label in zip(patient_data, labels):

        if label not in clusters:
            clusters[label] = []

        clusters[label].append(item["patient_id"])

    return clusters


def get_disease_group_name(patient_ids, db: Session):

    records = (
        db.query(MedicalHistory)
        .filter(MedicalHistory.patient_id.in_(patient_ids))
        .all()
    )

    text = " ".join(
        f"{record.problem or ''} "
        f"{record.diagnosis or ''} "
        f"{record.notes or ''}"
        for record in records
    ).lower()

    if "fever" in text or "flu" in text or "cold" in text:
        return "Fever/Flu type"

    if "headache" in text or "migraine" in text:
        return "Headache/Migraine type"

    if "skin" in text or "rash" in text or "itching" in text:
        return "Skin related"

    return "Other"


def save_clusters_to_database(clusters, db: Session):

    db.query(DiseaseGroup).delete()

    for cluster_id, patient_ids in clusters.items():

        disease_group = get_disease_group_name(
            patient_ids=patient_ids,
            db=db
        )

        cluster = DiseaseGroup(
            cluster_id=cluster_id + 1,
            disease_group=disease_group,
            patient_ids=",".join(
                str(patient_id)
                for patient_id in patient_ids
            )
        )

        db.add(cluster)

    db.commit()


def run_disease_clustering(db: Session, n_clusters=3):

    records = get_medical_history(db)

    if not records:
        return {
            "success": False,
            "message": "No medical history found."
        }

    patient_data = prepare_patient_text(records)

    X, vectorizer = create_vectors(patient_data)

    labels, kmeans = create_clusters(
        X,
        n_clusters=n_clusters
    )

    clusters = group_patients(
        patient_data,
        labels
    )

    save_clusters_to_database(
        clusters,
        db
    )

    return {
        "success": True,
        "clusters": clusters
    }
if __name__ == "__main__":

    from clinic_assistant.database.connection import SessionLocal

    db = SessionLocal()

    try:
        result = run_disease_clustering(
    db=db,
    n_clusters=3
)

    finally:
        db.close()