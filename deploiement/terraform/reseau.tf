resource "aws_vpc" "atelier" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_internet_gateway" "sortie" {
  vpc_id = aws_vpc.atelier.id
}

resource "aws_subnet" "publics" {
  count                   = 2
  vpc_id                  = aws_vpc.atelier.id
  cidr_block              = "10.42.${count.index}.0/24"
  availability_zone       = local.zones[count.index]
  map_public_ip_on_launch = false
}

resource "aws_subnet" "prives" {
  count             = 2
  vpc_id            = aws_vpc.atelier.id
  cidr_block        = "10.42.${count.index + 10}.0/24"
  availability_zone = local.zones[count.index]
}

resource "aws_route_table" "publique" {
  vpc_id = aws_vpc.atelier.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.sortie.id
  }
}

resource "aws_route_table_association" "publiques" {
  count          = 2
  subnet_id      = aws_subnet.publics[count.index].id
  route_table_id = aws_route_table.publique.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.atelier.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.publique.id]
}

resource "aws_security_group" "entree" {
  name   = "${var.nom}-entree"
  vpc_id = aws_vpc.atelier.id
}

resource "aws_security_group" "application" {
  name   = "${var.nom}-application"
  vpc_id = aws_vpc.atelier.id
}

resource "aws_security_group" "base" {
  name   = "${var.nom}-base"
  vpc_id = aws_vpc.atelier.id
}

resource "aws_vpc_security_group_ingress_rule" "web" {
  for_each          = toset(["80", "443"])
  security_group_id = aws_security_group.entree.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
}

resource "aws_vpc_security_group_egress_rule" "entree_application" {
  security_group_id            = aws_security_group.entree.id
  referenced_security_group_id = aws_security_group.application.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

resource "aws_vpc_security_group_ingress_rule" "application" {
  security_group_id            = aws_security_group.application.id
  referenced_security_group_id = aws_security_group.entree.id
  ip_protocol                  = "tcp"
  from_port                    = 3000
  to_port                      = 3000
}

resource "aws_vpc_security_group_egress_rule" "internet_application" {
  for_each          = toset(["80", "443"])
  security_group_id = aws_security_group.application.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = tonumber(each.value)
  to_port           = tonumber(each.value)
}

resource "aws_vpc_security_group_egress_rule" "application_base" {
  security_group_id            = aws_security_group.application.id
  referenced_security_group_id = aws_security_group.base.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_ingress_rule" "base" {
  security_group_id            = aws_security_group.base.id
  referenced_security_group_id = aws_security_group.application.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
