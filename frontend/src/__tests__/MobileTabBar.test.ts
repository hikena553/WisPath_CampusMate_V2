import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MobileTabBar from '../components/responsive/MobileTabBar.vue'

describe('MobileTabBar', () => {
  const items = [
    { key: 'home', label: '首页', icon: undefined, route: '/' },
    { key: 'discover', label: '发现', icon: undefined, route: '/discover' },
  ]

  it('renders all tab items', () => {
    const wrapper = mount(MobileTabBar, {
      props: { items, activeKey: 'home' },
    })
    const tabs = wrapper.findAll('.tab-item')
    expect(tabs).toHaveLength(2)
    expect(tabs[0].text()).toContain('首页')
    expect(tabs[1].text()).toContain('发现')
  })

  it('highlights the active tab', () => {
    const wrapper = mount(MobileTabBar, {
      props: { items, activeKey: 'home' },
    })
    const tabs = wrapper.findAll('.tab-item')
    expect(tabs[0].classes()).toContain('active')
    expect(tabs[1].classes()).not.toContain('active')
  })

  it('emits select event on click', async () => {
    const wrapper = mount(MobileTabBar, {
      props: { items, activeKey: 'home' },
    })
    await wrapper.findAll('.tab-item')[1].trigger('click')
    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0][0]).toEqual(items[1])
  })
})
