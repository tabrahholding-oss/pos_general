frappe.ui.form.on('Sales Order', {
	refresh: function(frm) {
        frm.set_query('table_no',(frm)=>{
            return{
                filters:{
                    "status": ["!=","Reserved"]
                }
            }
        });
	}
});
