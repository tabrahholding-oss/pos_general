import frappe

@frappe.whitelist()
def get_cost_center_from_pos_profile(user):
    cost_center=[]
    pos_profile_list = frappe.get_list("POS Profile")
    if len(pos_profile_list)>0:
        for pos_name in pos_profile_list:
            profile_doc = frappe.get_doc("POS Profile",pos_name.name)
            for usr in profile_doc.applicable_for_users:
                if user in usr.user:
                    if profile_doc.cost_center not in cost_center:
                        cost_center.append(profile_doc.cost_center)
    return cost_center