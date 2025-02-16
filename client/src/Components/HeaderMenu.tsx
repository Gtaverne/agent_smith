import { IconChevronDown } from "@tabler/icons-react";
import { Burger, Center, Group, Menu, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import classes from "./HeaderMenu.module.css";

const links = [
  { link: "/about", label: "Team" },
  //   {
  //     link: "#1",
  //     label: "Learn",
  //     links: [
  //       { link: "/docs", label: "Documentation" },
  //       { link: "/resources", label: "Resources" },
  //       { link: "/community", label: "Community" },
  //       { link: "/blog", label: "Blog" },
  //     ],
  //   },
  //   { link: "/about", label: "About" },
  //   { link: "/pricing", label: "Pricing" },
  //   {
  //     link: "#2",
  //     label: "Support",
  //     links: [
  //       { link: "/faq", label: "FAQ" },
  //       { link: "/demo", label: "Book a demo" },
  //       { link: "/forums", label: "Forums" },
  //     ],
  //   },
];

export function HeaderMenu() {
  const [opened, { toggle }] = useDisclosure(false);

  const items = links.map((link) => {
    // const menuItems = link.links?.map((item) => (
    //   <Menu.Item key={item.link}>{item.label}</Menu.Item>
    // ));

    // if (menuItems) {
    //   return (
    //     <Menu
    //       key={link.label}
    //       trigger="hover"
    //       transitionProps={{ exitDuration: 0 }}
    //       withinPortal
    //     >
    //       <Menu.Target>
    //         <a
    //           href={link.link}
    //           className={classes.link}
    //           onClick={(event) => event.preventDefault()}
    //         >
    //           <Center>
    //             <span className={classes.linkLabel}>{link.label}</span>
    //             <IconChevronDown size={14} stroke={1.5} />
    //           </Center>
    //         </a>
    //       </Menu.Target>
    //       <Menu.Dropdown>{menuItems}</Menu.Dropdown>
    //     </Menu>
    //   );
    // }

    return (
      <a
        key={link.label}
        href={link.link}
        className={classes.link}
        onClick={(event) => event.preventDefault()}
      >
        {link.label}
      </a>
    );
  });

  return (
    <header className={classes.header}>
      <div className={classes.inner}>
        <Title ml="lg">🫧 Bubble Buster</Title>
        <Group gap={5} visibleFrom="sm" mr="lg">
          {items}
        </Group>
        <Burger
          opened={opened}
          onClick={toggle}
          size="sm"
          hiddenFrom="sm"
          mr="lg"
        />
      </div>
    </header>
  );
}
