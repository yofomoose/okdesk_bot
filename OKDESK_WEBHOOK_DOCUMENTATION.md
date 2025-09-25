okdesk_webhooks:
  description: "HTTP(S) notifications about events in OKDesk system"
  structure: "All webhooks contain 'event' and entity-specific data blocks"

# TICKETS (Issues/Заявки)
tickets:
  common_structure:
    id: string
    title: string
    planned_execution_in_hours: string
    spent_time_total: string
    parent_id: string|null
    child_ids: [int]
    description: string

    type:
      code: string # service|incident
      name: string
      inner: boolean

    priority:
      code: string # low|normal|high|critical
      name: string

    status:
      code: string # opened|in_progress|completed|closed
      name: string

    old_status:
      code: string
      name: string

    rate: string # poor|normal|good|excellent

    client:
      company: {id: string, name: string}
      contact: {id: string, first_name: string, last_name: string, patronymic: string}

    agreement: {id: string, title: string}

    maintenance_entity:
      id: string
      name: string
      address: {string_value: string, coordinates: [lat, lng]}
      timezone: string
      schedule: {id: string, name: string}

    equipments:
      - id: string
        serial_number: string
        inventory_number: string
        type: {code: string, name: string}
        manufacturer: {code: string, name: string}
        model: {code: string, name: string}

    author: {id: string, first_name: string, last_name: string, patronymic: string, type: "employee|contact"}

    assignee:
      group: {id: string, name: string}
      employee: {id: string, first_name: string, last_name: string, patronymic: string}

    coexecutors: [assignee_structure]

    observers:
      employees: [person_structure]
      contacts: [person_structure]
      groups: [{id: string, name: string}]

    created_at: "ISO8601"
    deadline_at: "ISO8601"
    planned_reaction_at: "ISO8601"
    start_execution_until: "ISO8601"
    completed_at: "ISO8601|null"
    reacted_at: "ISO8601"

    parameters: [custom_parameter_structure]
    attachments: [attachment_structure]

  events:
    new_ticket:
      event_type: "new_ticket"
      source: "from_employee|from_contact|from_email"
      webhook: {event: event_data, issue: common_structure}

    new_ticket_status:
      event_type: "new_ticket_status"
      author: person_structure
      old_status: status_structure
      new_status: status_structure
      comment: {id: string, is_public: boolean, content: string}
      attachments: [attachment_structure]
      parameters: [custom_parameter_structure]
      time_entries: {id: string, comment: string, spent_time: string, logged_at: "ISO8601", employee: person_structure}
      old_assignee: assignee_structure
      new_assignee: assignee_structure
      webhook: {event: event_data, issue: common_structure}

    new_assignee:
      event_type: "new_assignee"
      author: person_structure
      old_assignee: assignee_structure
      new_assignee: assignee_structure
      webhook: {event: event_data, issue: common_structure}

    update_issue_work_type:
      event_type: "update_issue_work_type"
      old_type: type_structure
      new_type: type_structure
      author: person_structure
      webhook: {event: event_data, issue: common_structure}

    new_comment:
      event_type: "new_comment"
      author: person_structure
      comment: {id: string, is_public: boolean, content: string}
      attachments: [attachment_structure]
      webhook: {event: event_data, issue: common_structure}

    new_csat_rate:
      event_type: "new_csat_rate"
      rate: string # poor|normal|good|excellent
      author: person_structure
      webhook: {event: event_data, issue: common_structure}

    new_files:
      event_type: "new_files"
      author: person_structure
      attachments: [attachment_structure]
      webhook: {event: event_data, issue: common_structure}

    new_deadline:
      event_type: "new_deadline"
      deadline_at:
        auto_recount: boolean
        old_value: "ISO8601"
        new_value: "ISO8601"
      author: person_structure
      webhook: {event: event_data, issue: common_structure}

    add_coexecutor:
      event_type: "add_coexecutor"
      author: person_structure
      coexecutor: assignee_structure
      webhook: {event: event_data, issue: common_structure}

    remove_coexecutor:
      event_type: "remove_coexecutor"
      author: person_structure
      coexecutor: assignee_structure
      webhook: {event: event_data, issue: common_structure}

    change_ticket_parameter:
      event_type: "change_ticket_parameter"
      author: person_structure
      changed_parameters:
        - code: string
          before: string
          after: string
      webhook: {event: event_data, issue: common_structure}

    ticket_deleted:
      event_type: "ticket_deleted"
      author: person_structure
      webhook: {event: event_data, issue: partial_structure}
      note: "Issue data is partial for deleted tickets"

# EQUIPMENT (Оборудование)
equipment:
  common_structure:
    id: string
    equipment_kind: {id: string, code: string, name: string}
    equipment_manufacturer: {id: string, code: string, name: string}
    equipment_model: {id: string, code: string, name: string}
    serial_number: string
    inventory_number: string
    comment: string
    company: {id: string, name: string}
    maintenance_entity: {id: string, name: string}
    agreements: [{id: string, name: string}]
    parameters: [custom_parameter_structure]
    created_at: "ISO8601"
    author: person_structure

  events:
    new_equipment:
      event_type: "new_equipment"
      webhook: {event: event_data, equipment: common_structure}

    change_equipment:
      event_type: "change_equipment"
      author: person_structure
      changes:
        - parameters: [parameter_change_structure]
        - code: "company_id|maintenance_entity_id|serial_number|inventory_number|agreement_ids|comment|equipment_manufacturer_id|equipment_model_id|equipment_kind_id"
          old_value: any
          new_value: any
      webhook: {event: event_data, equipment: common_structure}

# COMPANIES (Компании)
companies:
  common_structure:
    id: string
    name: string
    additional_name: string
    site: string
    email: string
    phone: string
    active: boolean

    observers:
      employees: [person_with_login_structure]
      contacts: [person_with_login_structure]
      groups: [{id: string, name: string}]

    assignee:
      employee: person_with_login_structure
      group: {id: string, name: string}

    address:
      string_value: string
      coordinates: [lat, lng]

    category: {code: string, name: string}
    parameters: [custom_parameter_structure]
    created_at: "ISO8601"

  events:
    new_company:
      event_type: "new_company"
      author: person_with_login_structure
      webhook: {event: event_data, company: common_structure}

    change_company:
      event_type: "change_company"
      author: person_with_login_structure
      changes:
        - parameters: [parameter_change_structure]
        - code: "name|additional_name|site|email|phone|address|comment|default_assignee_id|default_assignee_group_id|category_id|active|observer_ids|contact_observer_ids|observer_group_ids"
          old_value: any
          new_value: any
      webhook: {event: event_data, company: common_structure}

# AGREEMENTS (Договоры)
agreements:
  common_structure:
    id: string
    title: string
    active: boolean
    cost: string
    start_date: "ISO8601"
    end_date: "ISO8601"
    companies: [{id: string, name: string}]

    observers:
      employees: [person_structure]
      groups: [{id: string, name: string}]

    assignee:
      employee: person_structure
      group: {id: string, name: string}

    parameters: [custom_parameter_structure]
    created_at: "ISO8601"

  events:
    new_agreement:
      event_type: "new_agreement"
      author: person_structure
      webhook: {event: event_data, agreement: common_structure}

    change_agreement:
      event_type: "change_agreement"
      author: person_structure
      changes:
        - parameters: [parameter_change_structure]
        - code: "title|company_ids|default_assignee_id|default_assignee_group_id|observer_ids|observer_group_ids"
          old_value: any
          new_value: any
      webhook: {event: event_data, agreement: common_structure}

# SERVICE AIMS (Объекты обслуживания)
service_aims:
  common_structure:
    id: string
    name: string
    active: boolean
    timezone: string
    comment: string
    company: {id: string, name: string}
    schedule: {id: string, name: string}

    address:
      string_value: string
      coordinates: [lat, lng]

    agreements: [{id: string, title: string}]

    observers:
      employees: [person_structure]
      groups: [{id: string, name: string}]

    assignee:
      employee: person_structure
      group: {id: string, name: string}

    parameters: [custom_parameter_structure]
    created_at: "ISO8601"

  events:
    new_service_aim:
      event_type: "new_service_aim"
      author: person_structure
      webhook: {event: event_data, service_aim: common_structure}

    change_service_aim:
      event_type: "change_service_aim"
      author: person_structure
      changes:
        - parameters: [parameter_change_structure]
        - code: "name|company_id|timezone|active|address|agreement_ids|default_assignee_id|default_assignee_group_id|observer_ids|observer_group_ids|schedule_id|comment"
          old_value: any
          new_value: any
      webhook: {event: event_data, service_aim: common_structure}

# COMMON DATA STRUCTURES
common_structures:
  person_structure:
    id: string
    first_name: string
    last_name: string
    patronymic: string
    type: "employee|contact" # for authors

  person_with_login_structure:
    id: string
    first_name: string
    last_name: string
    patronymic: string
    login: string
    email: string

  assignee_structure:
    group: {id: string, name: string}
    employee: person_structure

  attachment_structure:
    id: string
    is_public: boolean
    attachment_file_name: string
    description: string
    attachment_file_size: string
    created_at: "ISO8601"

  custom_parameter_structure:
    code: string
    name: string
    type: "ftstring|ftdate|ftdatetime|ftcheckbox|ftselect|ftmultiselect"
    value: any

  parameter_change_structure:
    code: string
    name: string
    type: string
    old_value: any
    new_value: any

  status_structure:
    code: string
    name: string

  type_structure:
    code: string
    name: string
    inner: boolean # for tickets

# WEBHOOK DELIVERY
webhook_config:
  protocol: "HTTP(S)"
  method: "POST"
  content_type: "application/json"
  setup_url: "https://help.okdesk.ru/knowledge_base/articles/vebhuki-148"

# EVENT TYPES SUMMARY
event_types:
  tickets:
    - new_ticket
    - new_ticket_status
    - new_assignee
    - update_issue_work_type
    - new_comment
    - new_csat_rate
    - new_files
    - new_deadline
    - add_coexecutor
    - remove_coexecutor
    - change_ticket_parameter
    - ticket_deleted

  equipment:
    - new_equipment
    - change_equipment

  companies:
    - new_company
    - change_company

  agreements:
    - new_agreement
    - change_agreement

  service_aims:
    - new_service_aim
    - change_service_aim

# PARAMETER TYPES
parameter_types:
  ftstring: "String value"
  ftdate: "Date (YYYY-MM-DD)"
  ftdatetime: "DateTime (ISO8601)"
  ftcheckbox: "Boolean"
  ftselect: "Single select"
  ftmultiselect: "Multiple select"

# RATE VALUES
rate_values: ["poor", "normal", "good", "excellent"]

# STATUS CODES (common)
status_codes: ["opened", "in_progress", "completed", "closed"]

# TYPE CODES (tickets)
ticket_types: ["service", "incident"]

# PRIORITY CODES
priority_codes: ["low", "normal", "high", "critical"]