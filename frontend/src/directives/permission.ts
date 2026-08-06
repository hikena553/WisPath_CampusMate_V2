import type { Directive, DirectiveBinding } from 'vue'
import { hasPermission } from '@/utils/permission'
import { useAuthStore } from '@/stores/auth'

export const permissionDirective: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const permission = binding.value
    
    if (permission && !hasPermission(permission)) {
      el.style.display = 'none'
      el.setAttribute('data-permission-disabled', 'true')
    }
  },
  updated(el: HTMLElement, binding: DirectiveBinding) {
    const permission = binding.value
    
    if (permission && !hasPermission(permission)) {
      el.style.display = 'none'
      el.setAttribute('data-permission-disabled', 'true')
    } else {
      el.style.display = ''
      el.removeAttribute('data-permission-disabled')
    }
  },
}

export const roleDirective: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    let user = null
    try {
      user = useAuthStore().user
    } catch {
      return
    }
    const role = binding.value
    
    if (role && user?.role !== role) {
      el.style.display = 'none'
      el.setAttribute('data-role-disabled', 'true')
    }
  },
  updated(el: HTMLElement, binding: DirectiveBinding) {
    let user = null
    try {
      user = useAuthStore().user
    } catch {
      return
    }
    const role = binding.value
    
    if (role && user?.role !== role) {
      el.style.display = 'none'
      el.setAttribute('data-role-disabled', 'true')
    } else {
      el.style.display = ''
      el.removeAttribute('data-role-disabled')
    }
  },
}
