"""
Canonical Schema Models.

Factorized data model (dim/fact/bridge) that sits between staging and Odoo load.
Enables deduplication, natural key resolution, and dependency management.

Design Principles:
1. Minimal Redundancy: Dimensions stored once, facts reference via surrogate keys
2. 1:1 with Odoo: Each canonical table maps directly to one Odoo model
3. Clear Load Order: Dimensions → Facts → Bridges (matches Odoo dependencies)
4. Lineage Preserved: Every row tracks src_system, src_table, src_pk, src_hash
5. Idempotency Ready: Natural keys + content hashes enable safe replays
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Float, JSON, Boolean,
    Text, Date, CheckConstraint, Index, DECIMAL
)
from sqlalchemy.orm import relationship
from app.core.database import Base


# ============================================================================
# DIMENSION TABLES (Catalogs & Reference Data)
# ============================================================================

class DimPartner(Base):
    """
    Partner dimension (companies and contacts).

    Odoo Model: res.partner
    Natural Key: vat OR (name + street + city + state + country)
    """
    __tablename__ = "dim_partner"

    partner_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_table = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)
    src_hash = Column(String, nullable=False)

    # Natural keys (for deduplication)
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True)
    external_id = Column(String, nullable=True, unique=True)

    # Business attributes (normalized)
    is_company = Column(Boolean, nullable=False)
    parent_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), nullable=True)
    name = Column(String, nullable=False)
    vat = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    street = Column(String, nullable=True)
    street2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state_code = Column(String, nullable=True)  # Normalized to res.country.state.code
    country_code = Column(String(2), nullable=True)  # Normalized to ISO alpha-2
    zip = Column(String, nullable=True)
    type = Column(String, nullable=True)  # 'contact', 'invoice', 'delivery'
    company_sk = Column(Integer, ForeignKey("dim_company.company_sk"), nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    parent = relationship("DimPartner", remote_side=[partner_sk], backref="contacts")
    company = relationship("DimCompany", back_populates="partners")

    __table_args__ = (
        CheckConstraint("(is_company = 1) OR (parent_sk IS NOT NULL)", name="check_contact_has_parent"),
        Index("idx_dim_partner_natural_key", "natural_key_hash"),
        Index("idx_dim_partner_odoo_id", "odoo_id"),
        Index("idx_dim_partner_external_id", "external_id"),
    )


class DimUser(Base):
    """
    User dimension (Odoo users who own records).

    Odoo Model: res.users
    Natural Key: login
    """
    __tablename__ = "dim_user"

    user_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)

    # Natural key
    login = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True, unique=True)

    # Attributes
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    partner_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    partner = relationship("DimPartner")


class DimStage(Base):
    """
    CRM stage dimension.

    Odoo Model: crm.stage
    Natural Key: name + team_name (NULL = global)
    """
    __tablename__ = "dim_stage"

    stage_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Natural key
    name = Column(String, nullable=False)
    team_name = Column(String, nullable=True)  # NULL = global
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True, unique=True)

    # Attributes
    sequence = Column(Integer, nullable=False)
    is_won = Column(Boolean, default=False, nullable=False)
    fold = Column(Boolean, default=False, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


class DimLostReason(Base):
    """
    CRM lost reason dimension.

    Odoo Model: crm.lost.reason
    Natural Key: normalized name
    """
    __tablename__ = "dim_lost_reason"

    lost_reason_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Natural key
    name = Column(String, nullable=False)
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True, unique=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


class DimTag(Base):
    """
    CRM tag dimension.

    Odoo Model: crm.tag
    Natural Key: normalized name + company_sk
    """
    __tablename__ = "dim_tag"

    tag_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Natural key
    name = Column(String, nullable=False)
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True, unique=True)

    # Scope
    company_sk = Column(Integer, ForeignKey("dim_company.company_sk"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    company = relationship("DimCompany")


class DimUtmSource(Base):
    """UTM source dimension (e.g., google, facebook)."""
    __tablename__ = "dim_utm_source"

    utm_source_sk = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    natural_key_hash = Column(String, nullable=False, unique=True)
    odoo_id = Column(Integer, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


class DimUtmMedium(Base):
    """UTM medium dimension (e.g., cpc, email)."""
    __tablename__ = "dim_utm_medium"

    utm_medium_sk = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    natural_key_hash = Column(String, nullable=False, unique=True)
    odoo_id = Column(Integer, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


class DimUtmCampaign(Base):
    """UTM campaign dimension (e.g., spring-2024-promo)."""
    __tablename__ = "dim_utm_campaign"

    utm_campaign_sk = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    natural_key_hash = Column(String, nullable=False, unique=True)
    odoo_id = Column(Integer, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


class DimProduct(Base):
    """
    Product dimension.

    Odoo Model: product.product / product.template
    Natural Key: default_code (SKU)
    """
    __tablename__ = "dim_product"

    product_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)

    # Natural key
    default_code = Column(String, nullable=True)  # SKU
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_template_id = Column(Integer, nullable=True)  # product.template
    odoo_product_id = Column(Integer, nullable=True)   # product.product

    # Attributes
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'consu', 'service', 'product'
    list_price = Column(DECIMAL(15, 2), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


class DimCompany(Base):
    """
    Company dimension (Odoo multi-company).

    Odoo Model: res.company
    """
    __tablename__ = "dim_company"

    company_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=False, unique=True)

    # Attributes
    name = Column(String, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    partners = relationship("DimPartner", back_populates="company")


class DimPartnerCategory(Base):
    """
    Partner category dimension (res.partner.category tags).

    Odoo Model: res.partner.category
    Natural Key: normalized name + company_sk
    """
    __tablename__ = "dim_partner_category"

    category_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Natural key
    name = Column(String, nullable=False)
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True, unique=True)

    # Scope
    company_sk = Column(Integer, ForeignKey("dim_company.company_sk"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    company = relationship("DimCompany")


class DimActivityType(Base):
    """
    Activity type dimension (mail.activity.type).

    Odoo Model: mail.activity.type
    Natural Key: name
    """
    __tablename__ = "dim_activity_type"

    activity_type_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Natural key
    name = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True, unique=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


# ============================================================================
# FACT TABLES (Business Events)
# ============================================================================

class FactLead(Base):
    """
    CRM lead fact table.

    Odoo Model: crm.lead
    Natural Key: external_id OR (partner_sk + name + create_date[±3d])
    """
    __tablename__ = "fact_lead"

    lead_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_table = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)
    src_hash = Column(String, nullable=False)

    # Natural keys
    natural_key_hash = Column(String, nullable=False, unique=True)
    content_hash = Column(String, nullable=False)  # For change detection

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True)
    external_id = Column(String, nullable=True, unique=True)

    # Foreign keys (surrogate keys to dimensions)
    partner_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), nullable=True)
    user_sk = Column(Integer, ForeignKey("dim_user.user_sk"), nullable=False)
    stage_sk = Column(Integer, ForeignKey("dim_stage.stage_sk"), nullable=False)
    lost_reason_sk = Column(Integer, ForeignKey("dim_lost_reason.lost_reason_sk"), nullable=True)
    utm_source_sk = Column(Integer, ForeignKey("dim_utm_source.utm_source_sk"), nullable=True)
    utm_medium_sk = Column(Integer, ForeignKey("dim_utm_medium.utm_medium_sk"), nullable=True)
    utm_campaign_sk = Column(Integer, ForeignKey("dim_utm_campaign.utm_campaign_sk"), nullable=True)
    company_sk = Column(Integer, ForeignKey("dim_company.company_sk"), nullable=False)

    # Business attributes
    name = Column(String, nullable=False)
    contact_name = Column(String, nullable=True)
    email_from = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    expected_revenue = Column(DECIMAL(15, 2), nullable=True)
    probability = Column(DECIMAL(5, 2), nullable=True)
    date_open = Column(DateTime, nullable=True)
    date_closed = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    partner = relationship("DimPartner")
    user = relationship("DimUser")
    stage = relationship("DimStage")
    lost_reason = relationship("DimLostReason")
    company = relationship("DimCompany")

    __table_args__ = (
        Index("idx_fact_lead_natural_key", "natural_key_hash"),
        Index("idx_fact_lead_content_hash", "content_hash"),
        Index("idx_fact_lead_odoo_id", "odoo_id"),
        Index("idx_fact_lead_partner_sk", "partner_sk"),
    )


class FactActivity(Base):
    """
    Activity fact table (polymorphic).

    Odoo Model: mail.activity
    Natural Key: (res_model + res_id + activity_type_id + date_deadline + hash(note))
    """
    __tablename__ = "fact_activity"

    activity_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_table = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)
    src_hash = Column(String, nullable=False)

    # Natural key
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True)

    # Polymorphic link (anchor)
    anchor_model = Column(String, nullable=False)  # 'fact_lead' or 'dim_partner'
    anchor_sk = Column(Integer, nullable=False)    # FK to either fact_lead or dim_partner

    # Foreign keys
    user_sk = Column(Integer, ForeignKey("dim_user.user_sk"), nullable=False)
    activity_type_sk = Column(Integer, ForeignKey("dim_activity_type.activity_type_sk"), nullable=False)

    # Attributes
    date_deadline = Column(Date, nullable=False)
    summary = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    sequence = Column(Integer, nullable=True)  # For ordering (from pivot)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    user = relationship("DimUser")
    activity_type = relationship("DimActivityType")

    __table_args__ = (
        CheckConstraint("anchor_model IN ('fact_lead', 'dim_partner')", name="check_activity_anchor_model"),
        Index("idx_fact_activity_anchor", "anchor_model", "anchor_sk"),
    )


class FactMessage(Base):
    """
    Message fact table (polymorphic chatter entries).

    Odoo Model: mail.message
    Natural Key: external message_id OR (model + res_id + date[±1m] + author_id + hash(subject+body))
    """
    __tablename__ = "fact_message"

    message_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)

    # Natural key
    natural_key_hash = Column(String, nullable=False, unique=True)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True)

    # Polymorphic link
    anchor_model = Column(String, nullable=False)
    anchor_sk = Column(Integer, nullable=False)

    # Foreign keys
    author_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), nullable=True)

    # Attributes
    subject = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    message_type = Column(String, nullable=False)  # 'email', 'comment', 'notification'
    date = Column(DateTime, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    author = relationship("DimPartner")

    __table_args__ = (
        CheckConstraint("anchor_model IN ('fact_lead', 'dim_partner')", name="check_message_anchor_model"),
    )


class FactOrder(Base):
    """
    Sales order fact table.

    Odoo Model: sale.order
    Natural Key: external_id OR (partner_sk + name + date_order)
    """
    __tablename__ = "fact_order"

    order_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)
    src_hash = Column(String, nullable=False)

    # Natural key
    natural_key_hash = Column(String, nullable=False, unique=True)
    content_hash = Column(String, nullable=False)

    # Odoo mapping
    odoo_id = Column(Integer, nullable=True)
    external_id = Column(String, nullable=True, unique=True)

    # Foreign keys
    partner_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), nullable=False)
    user_sk = Column(Integer, ForeignKey("dim_user.user_sk"), nullable=False)
    company_sk = Column(Integer, ForeignKey("dim_company.company_sk"), nullable=False)

    # Attributes
    name = Column(String, nullable=False)
    date_order = Column(DateTime, nullable=False)
    state = Column(String, nullable=False)
    amount_total = Column(DECIMAL(15, 2), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    partner = relationship("DimPartner")
    user = relationship("DimUser")
    company = relationship("DimCompany")


class FactOrderLine(Base):
    """
    Sales order line fact table.

    Odoo Model: sale.order.line
    """
    __tablename__ = "fact_order_line"

    line_sk = Column(Integer, primary_key=True, autoincrement=True)

    # Source lineage
    src_system = Column(String, nullable=False)
    src_pk = Column(String, nullable=False)

    # Foreign keys
    order_sk = Column(Integer, ForeignKey("fact_order.order_sk"), nullable=False)
    product_sk = Column(Integer, ForeignKey("dim_product.product_sk"), nullable=False)

    # Attributes
    product_uom_qty = Column(DECIMAL(15, 3), nullable=False)
    price_unit = Column(DECIMAL(15, 2), nullable=False)
    discount = Column(DECIMAL(5, 2), default=0, nullable=False)
    sequence = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    # Relationships
    order = relationship("FactOrder")
    product = relationship("DimProduct")


# ============================================================================
# BRIDGE TABLES (Many-to-Many Relationships)
# ============================================================================

class BridgePartnerContact(Base):
    """
    Explicit company ↔ contact relationships.
    """
    __tablename__ = "bridge_partner_contact"

    company_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), primary_key=True)
    person_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), primary_key=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("company_sk != person_sk", name="check_different_partners"),
    )


class BridgeTagsPartner(Base):
    """
    Partner ↔ category tags (res.partner.category).
    """
    __tablename__ = "bridge_tags_partner"

    partner_sk = Column(Integer, ForeignKey("dim_partner.partner_sk"), primary_key=True)
    tag_sk = Column(Integer, ForeignKey("dim_partner_category.category_sk"), primary_key=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)


class BridgeTagsLead(Base):
    """
    Lead ↔ CRM tags (crm.tag).
    """
    __tablename__ = "bridge_tags_lead"

    lead_sk = Column(Integer, ForeignKey("fact_lead.lead_sk"), primary_key=True)
    tag_sk = Column(Integer, ForeignKey("dim_tag.tag_sk"), primary_key=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    batch_id = Column(String, nullable=False)
